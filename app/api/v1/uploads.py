"""Presigned single-use upload endpoint for large binary documents.

Paired with the create_upload_url MCP tool (app.mcp.server) — lets an MCP
client push a file via a plain HTTP PUT with a signed, expiring URL instead
of routing bytes through a tool-call payload. Auth here is the HMAC
signature embedded in the URL, not the usual JWT bearer token, since the
caller may not hold (or need) a full admin session — see
app.services.upload_signing.
"""

import asyncio
import logging
import time
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse

from app.config import settings
from app.db.session import get_db_session
from app.models.database import ConsumedUploadToken
from app.services.upload_signing import verify_upload_signature

logger = logging.getLogger(__name__)

router = APIRouter()


@router.put("/{upload_id}")
async def consume_upload_url(
    upload_id: str,
    request: Request,
    kb_id: str = Query(...),
    filename: str = Query(...),
    expires: int = Query(...),
    sig: str = Query(...),
) -> JSONResponse:
    """Verify a presigned upload URL, enforce single-use, then ingest the
    raw request body as a new document in the target knowledge base."""
    if time.time() > expires:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Upload URL expired")

    if not verify_upload_signature(upload_id, kb_id, filename, expires, sig):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    try:
        kb_uuid = UUID(kb_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid kb_id")

    async with get_db_session() as db:
        # Atomically claim this upload_id — a unique-constraint violation means
        # the URL was already consumed (or is being consumed concurrently).
        db.add(ConsumedUploadToken(upload_id=upload_id))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Upload URL already used"
            )

        content_bytes = await request.body()
        if len(content_bytes) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File size {len(content_bytes)} bytes exceeds limit of "
                    f"{settings.MAX_FILE_SIZE_MB}MB"
                ),
            )

        from app.api.v1.documents import create_document as _api_create_document

        upload_file = UploadFile(BytesIO(content_bytes), filename=filename, size=len(content_bytes))
        background_tasks = BackgroundTasks()

        doc = await _api_create_document(
            file=upload_file,
            knowledge_base_id=kb_uuid,
            detect_duplicates=False,
            contextual_description_enabled=None,
            background_tasks=background_tasks,
            db=db,
            user_id=None,
        )

    asyncio.create_task(background_tasks())

    logger.info(f"Presigned upload consumed: document {doc.id} ({filename})")
    return JSONResponse(
        {"document_id": str(doc.id), "filename": filename, "bytes": len(content_bytes)}
    )

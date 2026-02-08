"""Knowledge Base export/import endpoints (MVP)."""
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import KBExportRequest, KBImportOptions, KBImportResponse
from app.services.kb_export_import import export_kbs, import_kbs, KBExportImportError


router = APIRouter(prefix="/kb", tags=["kb-transfer"])


@router.post("/export")
async def export_kb(
    payload: KBExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Export one or more KBs as a compressed archive."""
    try:
        archive_path, archive_name = await export_kbs(db, payload.kb_ids, payload.include)
    except KBExportImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    def _cleanup(path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    background_tasks.add_task(_cleanup, archive_path)

    return FileResponse(
        path=archive_path,
        filename=archive_name,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{archive_name}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/import", response_model=KBImportResponse)
async def import_kb(
    file: UploadFile = File(...),
    options: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Import one or more KBs from an exported archive."""
    try:
        if options:
            options_payload = KBImportOptions(**json.loads(options))
        else:
            options_payload = KBImportOptions()

        import tempfile
        fd, temp_path = tempfile.mkstemp(prefix="kb_import_", suffix=".tar.gz")
        try:
            with os.fdopen(fd, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

            result = await import_kbs(db, temp_path, options_payload)
            return KBImportResponse(**result)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except KBExportImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid options JSON") from exc

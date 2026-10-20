"""
Per-user resource ownership (data isolation between admin accounts).

One admin account owns each knowledge base (set at creation, from the JWT
subject - app/dependencies.py::get_current_user_id). Documents and
conversations created inside that KB are stamped with the same owner, so
they stay in sync with it by construction rather than needing their own
separate access-control source of truth - app/api/v1/*.py check whichever
of the two is already in hand (the KB itself, or a document/conversation's
own user_id column) rather than always re-joining to the parent KB.

A resource with user_id=None is treated as accessible to everyone. That
covers legacy/pre-isolation rows that were deliberately left unowned (see
migration 4f2b8e91a3c7) and any future row that genuinely has no owner,
rather than making either case an inaccessible black hole.

check_ownership(..., current_user_id=None) is also a deliberate bypass
(access granted unconditionally), not "anonymous user, deny everything".
REST callers never actually pass None here - app.dependencies.get_current_user_id
raises 401 before returning, so it's always a real int by the time any
endpoint calls check_ownership. The one real caller of current_user_id=None
is app/mcp/server.py, which has no per-admin identity at all (MCP tokens
aren't threaded through to tool bodies) and, pre-isolation, always operated
on every knowledge base/document unconditionally - treating None as "skip
the check" preserves that existing behavior instead of silently breaking
every MCP delete/update call against now-owned data.
"""

from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, or_


def ownership_filter(user_id_column: Any, current_user_id: Optional[int]) -> ColumnElement[bool]:
    """
    SQLAlchemy filter clause for list queries: rows owned by
    current_user_id, or unowned (legacy/pre-isolation - see module
    docstring). Pass the model's own user_id column, e.g.
    ownership_filter(KnowledgeBaseModel.user_id, user_id).
    """
    return or_(user_id_column == current_user_id, user_id_column.is_(None))


def check_ownership(
    owner_id: Optional[int],
    current_user_id: Optional[int],
    resource: str = "resource",
) -> None:
    """
    Raise 403 if current_user_id does not own this resource.

    owner_id=None (unowned/legacy) is accessible to everyone - not a 403.
    current_user_id=None is a deliberate bypass (see module docstring) -
    also not a 403.
    """
    if current_user_id is None:
        return
    if owner_id is not None and owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have access to this {resource}",
        )

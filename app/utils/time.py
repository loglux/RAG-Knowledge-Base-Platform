"""Time utilities."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime.

    Drop-in replacement for ``datetime.utcnow()``, which is deprecated in
    Python 3.12+ and scheduled for removal. We keep the result naive to
    preserve compatibility with existing ``DateTime`` (without ``timezone=True``)
    columns and the comparisons that already exist in the codebase. Migrating
    to timezone-aware datetimes is a separate, larger refactor that would also
    require a database column migration.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

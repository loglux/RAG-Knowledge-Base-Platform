"""
Shared rate-limiter instance (slowapi, in-memory storage).

Single shared Limiter so both app.main (global middleware + default_limits)
and individual routers (per-route @limiter.limit(...) overrides) use the same
state - defining it here avoids a circular import between app.main and the
routers that need tighter limits (e.g. app/api/v1/auth.py).

In-memory storage is fine: each deployment runs exactly one `api` container
(no horizontal scaling), so there's no cross-process state to share.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

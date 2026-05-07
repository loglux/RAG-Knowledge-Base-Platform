"""Unit tests for app.api.v1.auth endpoints (mocked DB)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import auth as auth_core
from app.core.auth import REFRESH_TOKEN_TYPE, create_access_token, create_refresh_token
from app.db.session import get_db
from app.dependencies import get_current_admin_id
from app.main import app

# ---------- Helpers ---------------------------------------------------------


def make_admin(
    *,
    admin_id: int = 1,
    username: str = "alice",
    role: str = "admin",
    is_active: bool = True,
    password: str = "password123",
):
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    admin = MagicMock()
    admin.id = admin_id
    admin.username = username
    admin.role = role
    admin.is_active = is_active
    admin.password_hash = pw_hash
    admin.last_login = None
    return admin


def make_token_row(jti: str, *, revoked_at=None, expires_at=None):
    if expires_at is None:
        expires_at = datetime.utcnow() + timedelta(days=7)
    row = MagicMock()
    row.jti = jti
    row.revoked_at = revoked_at
    row.expires_at = expires_at
    return row


def make_db(*scalar_results):
    """Mock AsyncSession; each db.execute() call returns the next prescribed scalar value.

    With no scalar_results, db.execute() returns a default MagicMock for every call —
    useful when the endpoint runs UPDATE/INSERT statements and never reads scalars.
    """
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    if scalar_results:
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=r)) for r in scalar_results
        ]
    return db


def install_db(db):
    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override


def install_admin_id(admin_id: int):
    async def _override():
        return admin_id

    app.dependency_overrides[get_current_admin_id] = _override


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth_settings(monkeypatch):
    """Pin auth-related settings."""
    monkeypatch.setattr(auth_core.settings, "SECRET_KEY", "test-secret-32chars-xxxxxxxxxxxxx")
    monkeypatch.setattr(auth_core.settings, "ALGORITHM", "HS256")
    monkeypatch.setattr(auth_core.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    monkeypatch.setattr(auth_core.settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------- /auth/login -----------------------------------------------------


@pytest.mark.unit
class TestLogin:
    async def test_success_returns_tokens_and_sets_cookie(self, auth_settings, client):
        admin = make_admin(admin_id=42, username="alice", role="admin", password="hunter2")
        db = make_db(admin)
        install_db(db)

        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "hunter2"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["admin_id"] == 42
        assert body["username"] == "alice"
        assert body["role"] == "admin"
        assert body["access_token"]
        assert "refresh_token" in resp.cookies
        db.commit.assert_awaited_once()
        db.add.assert_called_once()

    async def test_user_not_found_returns_401(self, auth_settings, client):
        install_db(make_db(None))

        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "nope", "password": "x"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    async def test_inactive_user_returns_401(self, auth_settings, client):
        install_db(make_db(make_admin(is_active=False)))

        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "password123"},
        )

        assert resp.status_code == 401

    async def test_wrong_password_returns_401(self, auth_settings, client):
        install_db(make_db(make_admin(password="rightpw")))

        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "WRONG"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"


# ---------- /auth/refresh ---------------------------------------------------


@pytest.mark.unit
class TestRefresh:
    async def test_success_rotates_token(self, auth_settings, client):
        admin = make_admin(admin_id=7, username="bob", role="admin")
        token, jti, _ = create_refresh_token(admin_id=7)
        token_row = make_token_row(jti=jti)
        db = make_db(token_row, admin)
        install_db(db)

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["admin_id"] == 7
        assert body["username"] == "bob"
        assert "refresh_token" in resp.cookies
        assert resp.cookies["refresh_token"] != token  # rotated
        # The endpoint should mark old token revoked and add a new row.
        assert token_row.revoked_at is not None
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    async def test_missing_cookie_returns_401(self, auth_settings, client):
        install_db(make_db())  # never queried
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Missing refresh token"

    async def test_invalid_token_returns_401(self, auth_settings, client):
        install_db(make_db())
        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "not.a.valid.jwt"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid refresh token"

    async def test_wrong_token_type_returns_401(self, auth_settings, client):
        # Send an access token where a refresh token is expected.
        access = create_access_token(admin_id=1, username="u", role="admin")
        install_db(make_db())

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": access},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token type"

    async def test_token_row_not_found_returns_401(self, auth_settings, client):
        token, _, _ = create_refresh_token(admin_id=1)
        install_db(make_db(None))  # token_row lookup returns None

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Refresh token revoked"

    async def test_revoked_token_returns_401(self, auth_settings, client):
        token, jti, _ = create_refresh_token(admin_id=1)
        revoked = make_token_row(jti=jti, revoked_at=datetime.utcnow())
        install_db(make_db(revoked))

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Refresh token revoked"

    async def test_expired_token_row_returns_401(self, auth_settings, client):
        token, jti, _ = create_refresh_token(admin_id=1)
        expired = make_token_row(jti=jti, expires_at=datetime.utcnow() - timedelta(seconds=1))
        install_db(make_db(expired))

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Refresh token expired"

    async def test_payload_missing_sub_or_jti_returns_401(self, auth_settings, client):
        # Forge a refresh token whose payload lacks `sub` and `jti`.
        forged = jwt.encode(
            {
                "type": REFRESH_TOKEN_TYPE,
                "exp": datetime.now(timezone.utc) + timedelta(days=1),
            },
            auth_core.settings.SECRET_KEY,
            algorithm=auth_core.settings.ALGORITHM,
        )
        install_db(make_db())

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": forged},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid refresh token"

    async def test_admin_missing_returns_401(self, auth_settings, client):
        token, jti, _ = create_refresh_token(admin_id=99)
        install_db(make_db(make_token_row(jti=jti), None))  # token ok, admin lookup returns None

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "User not found"


# ---------- /auth/logout ----------------------------------------------------


@pytest.mark.unit
class TestLogout:
    async def test_with_valid_cookie_revokes_and_clears(self, auth_settings, client):
        token, _, _ = create_refresh_token(admin_id=1)
        db = make_db()  # logout uses execute(update(...)) — no scalar lookup
        install_db(db)

        resp = await client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 200
        assert resp.json() == {"success": True}
        db.execute.assert_awaited_once()
        db.commit.assert_awaited_once()

    async def test_without_cookie_succeeds(self, auth_settings, client):
        db = make_db()
        install_db(db)

        resp = await client.post("/api/v1/auth/logout")

        assert resp.status_code == 200
        assert resp.json() == {"success": True}
        db.execute.assert_not_called()

    async def test_with_invalid_cookie_succeeds_silently(self, auth_settings, client):
        db = make_db()
        install_db(db)

        resp = await client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": "garbage"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"success": True}
        # Decode failure path swallows the exception and never hits the DB.
        db.execute.assert_not_called()


# ---------- /auth/me --------------------------------------------------------


@pytest.mark.unit
class TestMe:
    async def test_returns_admin_info(self, auth_settings, client):
        admin = make_admin(admin_id=5, username="carol", role="admin")
        install_db(make_db(admin))
        install_admin_id(5)

        resp = await client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        body = resp.json()
        assert body["admin_id"] == 5
        assert body["username"] == "carol"
        assert body["role"] == "admin"

    async def test_admin_not_found_returns_404(self, auth_settings, client):
        install_db(make_db(None))
        install_admin_id(999)

        resp = await client.get("/api/v1/auth/me")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    async def test_unrouted_url_still_returns_generic_404(self, client):
        # Sanity check: the global 404 handler keeps the helpful generic body
        # for URLs that don't match any route.
        resp = await client.get("/api/v1/this-route-does-not-exist")

        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"] == "Endpoint not found"
        assert "suggestion" in body

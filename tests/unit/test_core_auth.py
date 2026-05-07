"""Unit tests for app.core.auth (JWT helpers)."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core import auth as auth_module
from app.core.auth import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_admin_id,
    is_token_type,
)


@pytest.fixture
def auth_settings(monkeypatch):
    """Pin auth-related settings so tests don't depend on env state."""
    monkeypatch.setattr(auth_module.settings, "SECRET_KEY", "test-secret-32chars-xxxxxxxxxxxxx")
    monkeypatch.setattr(auth_module.settings, "ALGORITHM", "HS256")
    monkeypatch.setattr(auth_module.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    monkeypatch.setattr(auth_module.settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)


@pytest.mark.unit
class TestCreateAccessToken:
    def test_payload_round_trips(self, auth_settings):
        token = create_access_token(admin_id=42, username="alice", role="admin")
        payload = decode_token(token)

        assert payload["sub"] == "42"
        assert payload["username"] == "alice"
        assert payload["role"] == "admin"
        assert payload["type"] == ACCESS_TOKEN_TYPE
        assert "exp" in payload
        assert "iat" in payload

    def test_expiration_within_configured_window(self, auth_settings):
        before = datetime.now(timezone.utc)
        token = create_access_token(1, "u", "r")
        payload = decode_token(token)

        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > before
        assert exp - before <= timedelta(minutes=16)


@pytest.mark.unit
class TestCreateRefreshToken:
    def test_returns_token_jti_and_expires(self, auth_settings):
        token, jti, expires = create_refresh_token(admin_id=42)
        payload = decode_token(token)

        assert payload["sub"] == "42"
        assert payload["type"] == REFRESH_TOKEN_TYPE
        assert payload["jti"] == jti
        assert isinstance(expires, datetime)

    def test_jti_is_unique_across_calls(self, auth_settings):
        _, jti1, _ = create_refresh_token(1)
        _, jti2, _ = create_refresh_token(1)
        assert jti1 != jti2

    def test_expiration_matches_days_setting(self, auth_settings):
        before = datetime.utcnow()
        _, _, expires = create_refresh_token(1)
        delta = expires - before
        # Allow a 1-minute slack on either side.
        assert timedelta(days=7, minutes=-1) <= delta <= timedelta(days=7, minutes=1)


@pytest.mark.unit
class TestDecodeToken:
    def test_returns_dict_for_valid_token(self, auth_settings):
        token = create_access_token(1, "u", "r")
        assert isinstance(decode_token(token), dict)

    def test_garbage_token_raises(self, auth_settings):
        with pytest.raises(jwt.JWTError):
            decode_token("not.a.valid.token")

    def test_wrong_signature_raises(self, auth_settings, monkeypatch):
        token = create_access_token(1, "u", "r")
        monkeypatch.setattr(auth_module.settings, "SECRET_KEY", "different-secret-32chars-yyyyyy")
        with pytest.raises(jwt.JWTError):
            decode_token(token)

    def test_expired_token_raises(self, auth_settings):
        # Forge a token whose exp is already in the past.
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        forged = jwt.encode(
            {"sub": "1", "type": ACCESS_TOKEN_TYPE, "exp": past},
            auth_module.settings.SECRET_KEY,
            algorithm=auth_module.settings.ALGORITHM,
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(forged)


@pytest.mark.unit
class TestIsTokenType:
    def test_match_returns_true(self):
        assert is_token_type({"type": ACCESS_TOKEN_TYPE}, ACCESS_TOKEN_TYPE) is True

    def test_mismatch_returns_false(self):
        assert is_token_type({"type": ACCESS_TOKEN_TYPE}, REFRESH_TOKEN_TYPE) is False

    def test_missing_type_returns_false(self):
        assert is_token_type({}, ACCESS_TOKEN_TYPE) is False


@pytest.mark.unit
class TestGetAdminId:
    def test_valid_numeric_sub(self):
        assert get_admin_id({"sub": "42"}) == 42

    def test_missing_sub_returns_none(self):
        assert get_admin_id({}) is None

    def test_empty_sub_returns_none(self):
        assert get_admin_id({"sub": ""}) is None

    def test_non_numeric_sub_returns_none(self):
        assert get_admin_id({"sub": "abc"}) is None

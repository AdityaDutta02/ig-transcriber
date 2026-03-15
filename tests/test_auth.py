"""
Unit tests for the auth module.
"""

import os
from unittest.mock import MagicMock, patch

import bcrypt
import pytest


class TestLoadCredentials:
    """Tests for _load_credentials."""

    def test_no_env_var_returns_empty(self, monkeypatch):
        monkeypatch.delenv("AUTH_CREDENTIALS", raising=False)
        from auth import _load_credentials
        assert _load_credentials() == {}

    def test_single_credential(self, monkeypatch):
        monkeypatch.setenv("AUTH_CREDENTIALS", "user@test.com:$2b$12$hash")
        from auth import _load_credentials
        creds = _load_credentials()
        assert "user@test.com" in creds
        assert creds["user@test.com"] == "$2b$12$hash"

    def test_multiple_credentials(self, monkeypatch):
        monkeypatch.setenv("AUTH_CREDENTIALS", "a@b.com:hash1;c@d.com:hash2")
        from auth import _load_credentials
        creds = _load_credentials()
        assert len(creds) == 2
        assert creds["a@b.com"] == "hash1"
        assert creds["c@d.com"] == "hash2"

    def test_malformed_entry_skipped(self, monkeypatch):
        monkeypatch.setenv("AUTH_CREDENTIALS", "badentry;a@b.com:hash1")
        from auth import _load_credentials
        creds = _load_credentials()
        assert len(creds) == 1
        assert "a@b.com" in creds


class TestCheckEmailPassword:
    """Tests for _check_email_password."""

    def test_valid_password(self, monkeypatch):
        password = "testpassword123"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        monkeypatch.setenv("AUTH_CREDENTIALS", f"user@test.com:{hashed}")

        from auth import _check_email_password
        result = _check_email_password("user@test.com", password)

        assert result is not None
        assert result["email"] == "user@test.com"
        assert result["provider"] == "email"

    def test_invalid_password(self, monkeypatch):
        password = "testpassword123"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        monkeypatch.setenv("AUTH_CREDENTIALS", f"user@test.com:{hashed}")

        from auth import _check_email_password
        result = _check_email_password("user@test.com", "wrongpassword")

        assert result is None

    def test_unknown_email(self, monkeypatch):
        monkeypatch.setenv("AUTH_CREDENTIALS", "user@test.com:somehash")
        from auth import _check_email_password
        result = _check_email_password("unknown@test.com", "password")
        assert result is None

    def test_no_credentials_configured(self, monkeypatch):
        monkeypatch.delenv("AUTH_CREDENTIALS", raising=False)
        from auth import _check_email_password
        result = _check_email_password("user@test.com", "password")
        assert result is None


class TestCheckAuth:
    """Tests for check_auth."""

    def test_open_mode_when_no_auth_configured(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("AUTH_CREDENTIALS", raising=False)

        from auth import check_auth
        with patch("auth.st") as mock_st:
            mock_st.session_state = {}
            result = check_auth()
            assert result is True

    def test_authenticated_session_passes(self, monkeypatch):
        monkeypatch.setenv("AUTH_CREDENTIALS", "user@test.com:hash")

        from auth import check_auth
        with patch("auth.st") as mock_st:
            mock_st.session_state = {"authenticated": True}
            result = check_auth()
            assert result is True

    def test_unauthenticated_renders_login(self, monkeypatch):
        monkeypatch.setenv("AUTH_CREDENTIALS", "user@test.com:hash")

        from auth import check_auth
        with patch("auth.st") as mock_st, \
             patch("auth.render_login_page", return_value=False) as mock_login:
            mock_st.session_state = {}
            result = check_auth()
            assert result is False
            mock_login.assert_called_once()


class TestGetGoogleClientId:
    """Tests for _get_google_client_id."""

    def test_returns_client_id_when_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
        from auth import _get_google_client_id
        assert _get_google_client_id() == "test-client-id.apps.googleusercontent.com"

    def test_returns_none_when_not_set(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        from auth import _get_google_client_id
        assert _get_google_client_id() is None

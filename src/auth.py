"""
Authentication Module

Simple email/password + Google OAuth login for the Streamlit app.
Uses redirect-based OAuth2 flow for Google sign-in and bcrypt for
email/password verification.
"""

import os
import urllib.parse
from typing import Optional

import requests as http_requests
import streamlit as st
from loguru import logger


_LOGIN_CSS = """
<style>
.login-container {
    max-width: 420px;
    margin: 4rem auto 2rem auto;
    padding: 2.5rem;
    background-color: #1e293b;
    border: 1px solid #2d3f55;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.login-title {
    text-align: center;
    font-size: 1.5rem;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 0.25rem;
}
.login-subtitle {
    text-align: center;
    font-size: 0.875rem;
    color: #94a3b8;
    margin-bottom: 2rem;
}
.login-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 1.5rem 0;
    color: #64748b;
    font-size: 0.8rem;
}
.login-divider::before,
.login-divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background-color: #334155;
}
.google-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    width: 100%;
    padding: 0.65rem 1rem;
    background-color: #ffffff;
    color: #1f2937;
    border: none;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s;
    text-decoration: none;
}
.google-btn:hover {
    background-color: #f1f5f9;
}
.google-btn svg {
    width: 18px;
    height: 18px;
}
</style>
"""

_GOOGLE_SVG = (
    '<svg viewBox="0 0 24 24">'
    '<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 '
    '3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>'
    '<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 '
    '1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>'
    '<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A11.96 '
    '11.96 0 0 0 0 12c0 1.94.46 3.77 1.28 5.4l3.56-2.77-.01-.54z" fill="#FBBC05"/>'
    '<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 '
    '1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>'
    '</svg>'
)


def _get_google_client_id() -> Optional[str]:
    return os.environ.get("GOOGLE_CLIENT_ID")


def _get_google_client_secret() -> Optional[str]:
    return os.environ.get("GOOGLE_CLIENT_SECRET")


def _get_app_url() -> str:
    """Get the app's public URL for OAuth redirect."""
    return os.environ.get("APP_URL", "http://localhost:8501")


def _build_google_auth_url() -> Optional[str]:
    """Build the Google OAuth2 authorization URL."""
    client_id = _get_google_client_id()
    if not client_id:
        return None

    redirect_uri = _get_app_url()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def _exchange_google_code(code: str) -> Optional[dict]:
    """Exchange an authorization code for user info via Google OAuth2."""
    client_id = _get_google_client_id()
    client_secret = _get_google_client_secret()
    if not client_id or not client_secret:
        logger.error("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set")
        return None

    redirect_uri = _get_app_url()

    try:
        token_resp = http_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        userinfo_resp = http_requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

        return {
            "email": userinfo.get("email", ""),
            "name": userinfo.get("name", ""),
            "picture": userinfo.get("picture", ""),
            "provider": "google",
        }
    except Exception as exc:
        logger.warning(f"Google OAuth2 token exchange failed: {exc}")
        return None


def _load_credentials() -> dict:
    """Load email/password credentials from environment or config."""
    raw = os.environ.get("AUTH_CREDENTIALS", "")
    if not raw:
        return {}

    credentials = {}
    for entry in raw.split(";"):
        entry = entry.strip()
        if ":" not in entry:
            continue
        email, password = entry.split(":", 1)
        credentials[email.strip()] = password.strip()
    return credentials


def _check_email_password(email: str, password: str) -> Optional[dict]:
    """Validate email/password against stored credentials."""
    import bcrypt

    credentials = _load_credentials()
    if not credentials:
        logger.warning("No AUTH_CREDENTIALS configured")
        return None

    stored_hash = credentials.get(email)
    if not stored_hash:
        return None

    try:
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return {
                "email": email,
                "name": email.split("@")[0],
                "provider": "email",
            }
    except Exception as exc:
        logger.warning(f"Password verification failed: {exc}")

    return None


def _render_google_signin() -> None:
    """Render Google Sign-In as a redirect link button."""
    auth_url = _build_google_auth_url()
    if not auth_url:
        return

    st.link_button(
        "Sign in with Google",
        url=auth_url,
        use_container_width=True,
    )


def render_login_page() -> bool:
    """Render the login page. Returns True if user is authenticated."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="login-title">Video Transcriber</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="login-subtitle">Sign in to continue</div>',
        unsafe_allow_html=True,
    )

    # Check for Google OAuth2 callback code in query params
    params = st.query_params
    auth_code = params.get("code")
    if auth_code:
        user_info = _exchange_google_code(auth_code)
        if user_info:
            st.session_state["authenticated"] = True
            st.session_state["user"] = user_info
            st.query_params.clear()
            st.rerun()
            return True
        else:
            st.error("Google sign-in failed. Please try again.")
            st.query_params.clear()

    # Google Sign-In
    client_id = _get_google_client_id()
    if client_id:
        _render_google_signin()
        st.markdown(
            '<div class="login-divider">or</div>',
            unsafe_allow_html=True,
        )

    # Email/Password form
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com", key="login_email")
        password = st.text_input(
            "Password", type="password", placeholder="Enter your password", key="login_password"
        )
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return False

        user_info = _check_email_password(email, password)
        if user_info:
            st.session_state["authenticated"] = True
            st.session_state["user"] = user_info
            logger.info(f"User logged in: {user_info['email']} via {user_info['provider']}")
            st.rerun()
            return True
        else:
            st.error("Invalid email or password.")
            return False

    return False


def check_auth() -> bool:
    """Check if the current session is authenticated.

    Returns True if authenticated, False otherwise.
    Renders the login page when not authenticated.
    """
    # Skip auth if no credentials are configured (open mode)
    has_google = bool(_get_google_client_id())
    has_email_creds = bool(os.environ.get("AUTH_CREDENTIALS"))

    if not has_google and not has_email_creds:
        return True

    if st.session_state.get("authenticated"):
        return True

    render_login_page()
    return False


def render_user_menu() -> None:
    """Render user info and logout button in the sidebar."""
    user = st.session_state.get("user")
    if not user:
        return

    with st.sidebar:
        st.markdown("### Account")
        display_name = user.get("name", user.get("email", "User"))
        provider = user.get("provider", "email")
        st.caption(f"{display_name} ({provider})")

        if st.button("Sign out", key="logout_btn", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user"] = None
            logger.info(f"User logged out: {user.get('email', 'unknown')}")
            st.rerun()

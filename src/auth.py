"""
Authentication Module

Simple email/password + Google OAuth login for the Streamlit app.
Uses streamlit-authenticator for credential management and
google-auth-oauthlib for Google sign-in.
"""

import os
from typing import Optional

import streamlit as st
from loguru import logger

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ImportError:
    id_token = None
    google_requests = None
    logger.warning("google-auth not installed — Google login unavailable")


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


def _verify_google_token(token: str) -> Optional[dict]:
    """Verify a Google ID token and return user info."""
    if id_token is None or google_requests is None:
        logger.error("google-auth not installed")
        return None

    client_id = _get_google_client_id()
    if not client_id:
        logger.error("GOOGLE_CLIENT_ID not set")
        return None

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )
        return {
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
            "provider": "google",
        }
    except ValueError as exc:
        logger.warning(f"Google token verification failed: {exc}")
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
    """Render Google Sign-In button using Streamlit's component API."""
    client_id = _get_google_client_id()
    if not client_id:
        return

    google_auth_html = f"""
    <div id="g_id_onload"
         data-client_id="{client_id}"
         data-callback="handleCredentialResponse"
         data-auto_prompt="false">
    </div>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <script>
    function handleCredentialResponse(response) {{
        const token = response.credential;
        // Send token to Streamlit via query params
        const url = new URL(window.location.href);
        url.searchParams.set('google_token', token);
        window.location.href = url.toString();
    }}
    </script>
    <div id="g_id_signin"
         class="g_id_signin"
         data-type="standard"
         data-shape="rectangular"
         data-theme="filled_black"
         data-text="signin_with"
         data-size="large"
         data-width="360">
    </div>
    """
    st.components.v1.html(google_auth_html, height=50)


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

    # Check for Google OAuth callback token in query params
    params = st.query_params
    google_token = params.get("google_token")
    if google_token:
        user_info = _verify_google_token(google_token)
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

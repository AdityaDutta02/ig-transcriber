"""
UI Styles Module

Contains the CUSTOM_CSS constant for the modern dark shadcn-inspired theme.
"""

CUSTOM_CSS: str = """
<style>
/* ── Base ────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0f172a;
    color: #f8fafc;
}

[data-testid="stSidebar"] {
    background-color: #0f1f3d;
    border-right: 1px solid #2d3f55;
}

[data-testid="stSidebar"] * {
    color: #f8fafc;
}

/* ── Typography ──────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    color: #f8fafc !important;
    font-weight: 600;
}

p, span, label, div {
    color: #f8fafc;
}

.muted {
    color: #94a3b8;
    font-size: 0.875rem;
}

/* ── Cards ───────────────────────────────────────────────────────── */
.result-card {
    background-color: #1e293b;
    border: 1px solid #2d3f55;
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -1px rgba(0,0,0,0.2);
}

.result-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #2d3f55;
}

.result-card-title {
    font-size: 1rem;
    font-weight: 600;
    color: #f8fafc;
    margin: 0;
}

/* ── Metrics ─────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background-color: #1e293b;
    border: 1px solid #2d3f55;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #f8fafc !important;
    font-size: 1.25rem;
    font-weight: 600;
}

/* ── Primary Button ──────────────────────────────────────────────── */
[data-testid="stButton"] > button[kind="primary"] {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 0.625rem 1.25rem;
    font-weight: 600;
    width: 100%;
    transition: background-color 0.2s ease;
}

[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #4f46e5;
    border: none;
}

[data-testid="stButton"] > button[kind="primary"]:active {
    background-color: #4338ca;
    border: none;
}

/* ── Secondary / Download Buttons ───────────────────────────────── */
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stDownloadButton"] > button {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-weight: 500;
    width: 100%;
    transition: background-color 0.2s ease, border-color 0.2s ease;
}

[data-testid="stButton"] > button[kind="secondary"]:hover,
[data-testid="stDownloadButton"] > button:hover {
    background-color: #273549;
    border-color: #4f5f75;
}

/* ── Text Input ──────────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    padding: 0.625rem 0.875rem;
    font-size: 0.9rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

[data-testid="stTextInput"] input:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
    outline: none;
}

[data-testid="stTextInput"] input::placeholder {
    color: #64748b;
}

/* ── Text Area ───────────────────────────────────────────────────── */
[data-testid="stTextArea"] textarea {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    font-size: 0.85rem;
    line-height: 1.6;
}

[data-testid="stTextArea"] textarea:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}

/* ── Checkboxes ──────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label {
    color: #f8fafc;
    font-size: 0.9rem;
}

/* ── Sliders ─────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background-color: #6366f1;
}

/* ── Expander ────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background-color: #1e293b;
    border: 1px solid #2d3f55;
    border-radius: 8px;
}

[data-testid="stExpander"] summary {
    color: #f8fafc;
    font-weight: 500;
}

/* ── File Uploader ───────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background-color: #1e293b;
    border: 2px dashed #334155;
    border-radius: 8px;
    padding: 1rem;
}

[data-testid="stFileUploader"]:hover {
    border-color: #6366f1;
}

/* ── Alert / Info / Success / Error Boxes ────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px;
}

/* ── Divider ─────────────────────────────────────────────────────── */
hr {
    border-color: #2d3f55;
}

/* ── Download Source Badge ───────────────────────────────────────── */
.downloader-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 500;
    color: #94a3b8;
    vertical-align: middle;
}

.downloader-badge-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* green for yt-dlp (default / no class modifier) */
.downloader-badge-dot {
    background-color: #22c55e;
}

.downloader-badge-dot.fallback-1 {
    background-color: #f59e0b;
}

.downloader-badge-dot.fallback-2 {
    background-color: #f97316;
}

/* ── API Status Indicator ────────────────────────────────────────── */
.api-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    margin-bottom: 1rem;
    width: 100%;
}

.api-status.connected {
    background-color: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.3);
    color: #4ade80;
}

.api-status.disconnected {
    background-color: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #f87171;
}

.api-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

.api-status.connected .api-status-dot {
    background-color: #22c55e;
    box-shadow: 0 0 6px rgba(34, 197, 94, 0.6);
}

.api-status.disconnected .api-status-dot {
    background-color: #ef4444;
    box-shadow: 0 0 6px rgba(239, 68, 68, 0.6);
}

/* ── Platform Pill Badge ─────────────────────────────────────────── */
.platform-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 9999px;
    padding: 3px 12px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #a5b4fc;
    margin-bottom: 0.75rem;
}

/* ── Footer ──────────────────────────────────────────────────────── */
.footer {
    text-align: center;
    color: #475569;
    font-size: 0.8rem;
    padding: 1rem 0;
    border-top: 1px solid #2d3f55;
    margin-top: 2rem;
}

/* ── Sidebar Section Headers ─────────────────────────────────────── */
[data-testid="stSidebar"] h3 {
    color: #94a3b8 !important;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
}

/* ── Hide Streamlit Branding ─────────────────────────────────────── */
#MainMenu, footer[data-testid="stFooter"], header[data-testid="stHeader"] {
    visibility: hidden;
}

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: #0f172a;
}

::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
    background: #475569;
}
</style>
"""

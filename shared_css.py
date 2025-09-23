# shared_css.py
# Centralized stylesheet and helper for Streamlit pages & embedded HTML.

from __future__ import annotations

BOOTSTRAP_CDN = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
"""

CSS = """
body, .main, .block-container {
    font-family: 'Helvetica Neue', 'Segoe UI', 'Arial', sans-serif !important;
    background-color: #ffffff !important;
    color: #1a1a1a !important;
}
.block-container {
    max-width: 90vw !important;
    width: 90vw !important;
    min-width: 90vw !important;
    margin-left: 5vw !important;
}
header[data-testid="stHeader"] {
    background: none;
}
.ms-header {
    background: linear-gradient(90deg, #002855 70%, #0051a8 100%);
    color: #fff;
    padding: 2.5rem 0 1rem 0;
    border-radius: 0 0 16px 16px;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(0,40,85,0.08);
}
.ms-logo {
    height: 40px;
    margin-bottom: 1rem;
    filter: drop-shadow(0 2px 6px #00285530);
}
.ms-card {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 16px rgba(0,40,85,0.10);
    padding: 2rem 2rem 1.5rem 2rem;
    margin-bottom: 2rem;
    border: 1.5px solid #eaecef;
}
.ms-section-title {
    font-size: 1.45rem;
    color: #0051a8;
    font-weight: 600;
    margin-bottom: 1rem;
    letter-spacing: 1.5px;
    font-family: 'Helvetica Neue', 'Segoe UI', 'Arial', sans-serif !important;
}
.ms-success {
    background: #e0f0ff;
    border-left: 6px solid #0051a8;
    padding: 1.2rem 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    color: #002855;
    font-weight: 500;
}
.ms-footer {
    text-align: center;
    color: #002855;
    padding: 2.5rem 0 1.5rem 0;
    font-size: 1.1rem;
    letter-spacing: 1px;
    background: #f7f8fa;
    border-top: 2px solid #eaecef;
    margin-top: 2rem;
}
.ms-divider {
    border: none;
    border-top: 1px solid #eaecef;
    margin: 1rem 0;
}
.stButton>button {
    background: linear-gradient(90deg, #002855 70%, #0051a8 100%) !important;
    color: #fff !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.3rem !important;
    font-size: 1.1rem !important;
    box-shadow: 0 2px 8px rgba(0,40,85,0.12) !important;
    transition: background 0.2s;
}
.stButton>button:hover {
    background: #0051a8 !important;
    color: #fff !important;
}
.stExpander {
    border: 1px solid #eaecef !important;
    background: #f7f8fa !important;
    border-radius: 8px !important;
}
.badge-foundry {
    background: #0051a8;
    color: #fff;
    font-size: 1rem;
    padding: 0.3em 0.7em;
    border-radius: 0.6em;
    margin-left: 0.5em;
}
.bootstrap-icon {
    font-size: 1.15em;
    vertical-align: middle;
    color: #0051a8;
    margin-right: 0.25em;
}
@media (max-width: 1200px) {
    .block-container {
        max-width: 98vw !important;
        width: 98vw !important;
        min-width: 98vw !important;
        margin-left: 1vw !important;
    }
}
"""

def inject_shared_css(extra_css: str | None = None) -> None:
    """
    Inject Bootstrap + shared CSS into a Streamlit app.
    Optionally allow callers to append extra CSS safely.
    """
    import streamlit as st
    final_css = CSS + ("\n/* Extra overrides */\n" + extra_css if extra_css else "")
    st.markdown(BOOTSTRAP_CDN + f"<style>{final_css}</style>", unsafe_allow_html=True)

def inline_full_css(extra_css: str | None = None) -> str:
    """
    Return full HTML (Bootstrap links + style tag) for embedding into
    standalone HTML blocks (e.g., components, emails, exported HTML).
    """
    final_css = CSS + ("\n/* Extra overrides */\n" + extra_css if extra_css else "")
    return BOOTSTRAP_CDN + f"<style>{final_css}</style>"
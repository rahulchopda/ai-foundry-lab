import os
from typing import Dict

import fitz
import streamlit as st
import yaml

from model_orchestrator import ModelOrchestrator
from pii_analyzer import PIIHandler
from monitoring_web import generate_monitoring_html  # NEW IMPORT

# Initialize PII Handler
pii_handler = PIIHandler()

# --- Load Config ---
cfg = {}
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        st.warning(f"Could not load config.yaml: {e}")

model_endpoints = cfg.get("MODEL_ENDPOINTS", {})
api_key = cfg.get("API_KEY")
model_choices = cfg.get("MODEL_DEPLOYMENTS", [])
model_cost = cfg.get("MODEL_COST", {})

# Document processing functions
def extract_pdf_text(file_content) -> str:
    """Process uploaded PDF and return text content"""
    text = ""
    doc = fitz.open(stream=file_content, filetype="pdf")
    for page in doc:
        text += page.get_text()
    return text

# Model handler wrapper
def call_foundry_with_guardrails(endpoint: str, prompt: str, model_name: str) -> Dict:
    """Use ModelOrchestrator handler when available"""
    orchestrator = ModelOrchestrator(model_endpoints, api_key)
    handler = orchestrator.get_handler(model_name)
    print(f"Using handler {handler.__class__.__name__} with endpoint {handler.endpoint!r}")

    try:
        raw = handler.call(prompt)
        if isinstance(raw, str):
            return {
                "content": raw,
                "metrics": {},
                "guardrails": {},
                "monitoring": {}
            }
        return raw
    except Exception as e:
        return {
            "content": None,
            "error": str(e),
            "metrics": {},
            "guardrails": {},
            "monitoring": {}
        }

# Governance metrics (reserved for future use)
GOVERNANCE_METRICS = {
    "Model Usage": 324,
    "Team Accesses": 18,
    "Compliance Checks": "Passed",
    "Audit Trail": "Enabled",
    "Data Residency": "US/EU",
    "Last Model Update": "2025-09-10",
}

# Page config
st.set_page_config(
    page_title="Azure AI Foundry Playground",
    initial_sidebar_state="collapsed",
    layout="wide"
)

# Global CSS & Header (shared across both tabs)
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
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
</style>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

# Shared header
st.markdown("""
<div class="ms-header">
    <img src="https://www.morganstanley.com/etc/designs/mscorporate/clientlibs/mscorporate/resources/images/ms-logo.svg"
         class="ms-logo" alt="Morgan Stanley Logo" />
    <h1 style="margin-bottom:8px;font-family: 'Helvetica Neue', 'Segoe UI', 'Arial', sans-serif !important;">Gen AI Playground</h1>
    <span style="font-size:1.2rem;font-weight:400;">
        Experiment, Evaluate, Govern, and Monitor AI Models
        <span class="badge-foundry">Powered by Azure AI Foundry</span>
    </span>
</div>
""", unsafe_allow_html=True)

# Create tabs
tab_playground, tab_monitoring = st.tabs(["AI Playground", "Monitoring"])

# ---------------------- AI PLAYGROUND TAB ----------------------
with tab_playground:
    AVAILABLE_MODELS = ["mistral-small-2503", "Phi-4-mini-instruct", "gpt-4.1", "gpt-4.1-mini"]
    st.markdown('<div class="ms-section-title">Model Selection</div>', unsafe_allow_html=True)
    selected_models = []
    for m in AVAILABLE_MODELS:
        if st.checkbox(m, key=f"model_{m}"):
            selected_models.append(m)

    # Input Type
    st.markdown('<div class="ms-section-title">Input Data</div>', unsafe_allow_html=True)
    input_type = st.radio("Select input type", ["Text", "Document Upload"], horizontal=True)

    if input_type == "Text":
        input_text = st.text_area("Enter your input text here", height=180)
        doc_data = input_text
        doc_name = "Text Entered"
    else:
        uploaded_file = st.file_uploader("Upload a document (PDF)", type=["pdf"])
        doc_data = None
        doc_name = None
        if uploaded_file is not None:
            doc_name = uploaded_file.name
            file_size = len(uploaded_file.getvalue()) / 1024
            st.markdown(
                f'<div class="ms-success">File uploaded: <b>{doc_name}</b> ({file_size:.1f} KB)</div>',
                unsafe_allow_html=True
            )
            doc_data = extract_pdf_text(uploaded_file.getvalue()) if uploaded_file else ""

    # Optional PII detection
    if doc_data:
        st.markdown('<div class="ms-section-title">PII Detection</div>', unsafe_allow_html=True)
        run_pii = st.checkbox("Detect and redact sensitive information (PII)")
        if run_pii:
            try:
                with st.spinner("Detecting sensitive information..."):
                    pii_result = pii_handler.analyze_text(doc_data)
                    if pii_result["success"]:
                        if pii_result["entities"]:
                            st.markdown('<div class="ms-success">PII Detection Results</div>', unsafe_allow_html=True)
                            with st.expander("View Detected Sensitive Information"):
                                for entity in pii_result["entities"]:
                                    st.markdown(f"""
**{entity.category}** found:
- Text: `{entity.text}`
- Confidence: {entity.confidence_score:.2f}
""")
                            doc_data = pii_result["redacted_text"]
                            st.info("Input text has been redacted for sensitive information.")
                        else:
                            st.success("No sensitive information (PII) detected in the text.")
                    else:
                        st.error(f"PII detection failed: {pii_result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error during PII detection: {str(e)}")

    # Prompt
    st.markdown('<div class="ms-section-title">Prompt</div>', unsafe_allow_html=True)
    prompt = st.text_area("Enter your prompt here", height=180)

    # Execute models
    st.markdown('<div class="ms-section-title">Model Execution</div>', unsafe_allow_html=True)
    if st.button("Run Models with Guardrails", type="primary", use_container_width=True):
        if not doc_data:
            st.error("Please provide input text or upload a document first.")
            st.stop()

        final_prompt = (prompt or "") + ("\n\n" + doc_data if doc_data else "")
        st.markdown("#### Final Prompt")
        st.code(final_prompt, language="text")

        if not selected_models:
            st.error("Please select at least one model first.")
            st.stop()

        cols = st.columns(len(selected_models))
        for i, model_name in enumerate(selected_models):
            with cols[i]:
                st.markdown(f"**{model_name}**")
                try:
                    azure_endpoint = (model_endpoints.get(model_name, "") or "").strip()
                    raw = call_foundry_with_guardrails(azure_endpoint, final_prompt, model_name)

                    if isinstance(raw, dict) and raw.get("error"):
                        st.error(f"Handler error: {raw['error']}")
                        continue

                    # Expecting OpenAI-style response object
                    model_response = raw.choices[0].message.content
                    total_tokens = getattr(raw.usage, "total_tokens", None) or raw.usage.get("total_tokens")
                    safety = getattr(raw.choices[0], "content_filter_results", {}) or {}
                    safety_flags = sum(
                        1 for v in safety.values() if isinstance(v, dict) and v.get("filtered") is True
                    )
                    # Cost
                    cost_per_1m_tokens = cfg.get("MODEL_COST", {}).get(model_name, 0)
                    cost_estimate = (total_tokens / 1_000_000) * cost_per_1m_tokens if total_tokens else 0

                    st.subheader("Model Response")
                    st.write(model_response)

                    st.subheader("Total Tokens")
                    st.write(total_tokens)

                    st.subheader("Safety Flags")
                    st.write(safety_flags)

                    st.subheader("Cost Estimate")
                    st.write(f"{cost_estimate:.6f} (assuming {cost_per_1m_tokens}/1M tokens)")
                except Exception as e:
                    st.error(f"Error with {model_name}: {e}")

# ---------------------- MONITORING TAB ----------------------
with tab_monitoring:
    st.markdown('<div class="ms-section-title">Monitoring Dashboard</div>', unsafe_allow_html=True)

    # Optional auto-refresh
    refresh_seconds = st.slider("Auto-refresh interval (seconds)", 10, 300, 60)
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = 0

    # Simple manual refresh button
    if st.button("Refresh Now"):
        st.session_state.last_refresh += 1

    # Generate monitoring HTML (single consolidated dashboard)
    try:
        monitoring_html = generate_monitoring_html(
            governance_metrics=GOVERNANCE_METRICS,
            model_costs=model_cost,
            selected_models=None  # Could pass active models if needed
        )
        st.components.v1.html(monitoring_html, height=1400, scrolling=True)
    except Exception as e:
        st.error(f"Failed to render monitoring dashboard: {e}")

# Footer (shared)
st.markdown("""
<div class="ms-footer">
    Azure AI Foundry Playground by Morgan Stanley<br>
</div>
""", unsafe_allow_html=True)
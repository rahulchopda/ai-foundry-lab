import streamlit as st
import json
import os
import time
import yaml
from typing import Dict, List, Optional
import fitz
from azure.identity import DefaultAzureCredential
from model_orchestrator import ModelOrchestrator
from pii_analyzer import PIIHandler

try:
    from governance_logger import log_interaction, load_logs
    HAS_GOVERNANCE = True
except Exception:
    HAS_GOVERNANCE = False

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
prompt_templates = cfg.get("PROMPT_TEMPLATES", {})

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

GOVERNANCE_METRICS = {
    "Model Usage": 324,
    "Team Accesses": 18,
    "Compliance Checks": "Passed",
    "Audit Trail": "Enabled",
    "Data Residency": "US/EU",
    "Last Model Update": "2025-09-10",
}

# Set wide layout, remove sidebar
st.set_page_config(page_title="Azure AI Foundry Playground", layout="wide", initial_sidebar_state="collapsed")

# Inject Bootstrap CSS for professional widgets/icons and custom style for wide layout
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

# Morgan Stanley-style header
st.markdown("""
<div class="ms-header">
    <img src="https://www.morganstanley.com/etc/designs/mscorporate/clientlibs/mscorporate/resources/images/ms-logo.svg" class="ms-logo" alt="Morgan Stanley Logo" />
    <h1 style="margin-bottom:8px;font-family: 'Helvetica Neue', 'Segoe UI', 'Arial', sans-serif !important;">Gen AI Playground</h1>
    <span style="font-size:1.2rem;font-weight:400;">
        Experiment, Evaluate, Govern, and Monitor AI Models
        <span class="badge-foundry">Powered by Azure AI Foundry</span>
    </span>
</div>
""", unsafe_allow_html=True)

# --- Model selection ---
st.markdown('<div class="ms-section-title">Model Selection</div>', unsafe_allow_html=True)
if model_choices:
    selected_model = st.selectbox("Choose model:", model_choices)
else:
    st.warning("No models configured. Please check config.yaml")
    selected_model = None

# --- Input Text/Document ---
st.markdown('<div class="ms-section-title">Input Data</div>', unsafe_allow_html=True)
input_type = st.radio("Select input type", ["Text", "Document Upload"], horizontal=True)

if input_type == "Text":
    input_text = st.text_area("Enter your input text here", height=180)
    doc_data = input_text
    doc_name = "Text Entered"
elif input_type == "Document Upload":
    uploaded_file = st.file_uploader("Upload a document (PDF)", type=["pdf"])
    doc_data = None
    doc_name = None
    if uploaded_file is not None:
        doc_name = uploaded_file.name
        file_size = len(uploaded_file.getvalue()) / 1024  # KB
        st.markdown(
            f'<div class="ms-success">File uploaded: <b>{doc_name}</b> ({file_size:.1f} KB)</div>',
            unsafe_allow_html=True
        )
        if uploaded_file:
            doc_data = extract_pdf_text(uploaded_file.getvalue())
        else:
            doc_data = ""

# Add PII Detection option after input
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

                        # Show detected entities
                        with st.expander("View Detected Sensitive Information"):
                            for entity in pii_result["entities"]:
                                st.markdown(f"""
                                    **{entity.category}** found:
                                    - Text: `{entity.text}`
                                    - Confidence: {entity.confidence_score:.2f}
                                """)

                        # Update doc_data with redacted text
                        doc_data = pii_result["redacted_text"]
                        st.info("Input text has been redacted for sensitive information")
                    else:
                        st.success("No sensitive information (PII) detected in the text")
                else:
                    st.error(f"PII detection failed: {pii_result.get('error', 'Unknown error')}")

        except Exception as e:
            st.error(f"Error during PII detection: {str(e)}")

# Prompt
st.markdown('<div class="ms-section-title">Prompt</div>', unsafe_allow_html=True)
prompt = st.text_area("Enter your prompt here", height=180)

if st.button("Run Model with Guardrails", type="primary", use_container_width=True):
    if not doc_data:
        st.error("Please provide input text or upload a document first.")
        st.stop()

    if not selected_model:
        st.error("Please select a model first.")
        st.stop()

    st.markdown('<div class="ms-section-title">Processing</div>', unsafe_allow_html=True)
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Prepare prompt
        status_text.text("Preparing prompt...")
        progress_bar.progress(20)

        final_prompt = prompt + " " + doc_data

        # Display the final prompt
        st.markdown('<div class="ms-section-title">Final Prompt</div>', unsafe_allow_html=True)
        st.code(final_prompt, language="text")

        # Call model
        status_text.text("Calling AI model...")
        progress_bar.progress(50)

        azure_endpoint = model_endpoints.get(selected_model, "").strip()
        response = call_foundry_with_guardrails(azure_endpoint, final_prompt, selected_model)

        progress_bar.progress(100)
        status_text.text("Processing complete!")

        # Display results
        st.markdown('<div class="ms-section-title">Results</div>', unsafe_allow_html=True)

        # Model response
        st.markdown("### Model Response")
        st.write(response.get("content", "No response content."))

        # Metrics and governance
        st.markdown("### Processing Metrics")
        metrics_cols = st.columns(4)
        with metrics_cols[0]:
            st.metric("Model", selected_model)
        with metrics_cols[1]:
            st.metric("Tokens Used", response.get("metrics", {}).get("token_usage", "N/A"))
        with metrics_cols[3]:
            st.metric("Safety Flags", len(response.get("guardrails", {})))

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)
        if HAS_GOVERNANCE:
            log_interaction({
                "model": selected_model,
                "status": "error",
                "error": str(e)
            })

# Monitoring Section with HTML Files
st.markdown('<div class="ms-section-title">Monitoring Dashboard</div>', unsafe_allow_html=True)
monitoring_cols = st.columns(3)

with monitoring_cols[0]:
    st.markdown('<div class="ms-section-title">Model Performance Metrics</div>', unsafe_allow_html=True)
    with open(os.path.join(os.path.dirname(__file__), "io_metrics.html"), "r", encoding="utf-8") as f:
        st.components.v1.html(f.read(), height=400, scrolling=True)

with monitoring_cols[1]:
    st.markdown('<div class="ms-section-title">Request Count Over Time</div>', unsafe_allow_html=True)
    with open(os.path.join(os.path.dirname(__file__), "request_count.html"), "r", encoding="utf-8") as f:
        st.components.v1.html(f.read(), height=400, scrolling=True)

with monitoring_cols[2]:
    st.markdown('<div class="ms-section-title">Model Latency (ms)</div>', unsafe_allow_html=True)
    with open(os.path.join(os.path.dirname(__file__), "latency.html"), "r", encoding="utf-8") as f:
        st.components.v1.html(f.read(), height=400, scrolling=True)

st.markdown('<div class="ms-section-title">Governance Summary Metrics</div>', unsafe_allow_html=True)
if HAS_GOVERNANCE:
    logs = load_logs()
    if logs is not None and not logs.empty:
        st.dataframe(logs)
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Total Interactions", len(logs))
        with metric_cols[1]:
            if "latency_ms" in logs.columns:
                st.metric("Avg Latency (ms)", f"{logs['latency_ms'].mean():.2f}")
        with metric_cols[2]:
            if "tokens_used" in logs.columns:
                st.metric("Avg Tokens/Request", f"{logs['tokens_used'].mean():.1f}")
    else:
        st.info("No governance logs available yet.")
else:
    st.warning("Governance logging not available. Please check governance_logger.py")

# Footer
st.markdown("""
<div class="ms-footer">
    Azure AI Foundry Playground by Morgan Stanley<br>
</div>
""", unsafe_allow_html=True)
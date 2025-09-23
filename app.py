import os
from typing import Dict

import fitz
import streamlit as st
import yaml

from model_orchestrator import ModelOrchestrator
from pii_analyzer import PIIHandler
from monitoring_web import generate_monitoring_html
from shared_css import inject_shared_css  # NEW

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

def extract_pdf_text(file_content) -> str:
    text = ""
    doc = fitz.open(stream=file_content, filetype="pdf")
    for page in doc:
        text += page.get_text()
    return text

def call_foundry_with_guardrails(endpoint: str, prompt: str, model_name: str) -> Dict:
    orchestrator = ModelOrchestrator(model_endpoints, api_key)
    handler = orchestrator.get_handler(model_name)
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

st.set_page_config(
    page_title="Azure AI Foundry Playground",
    initial_sidebar_state="collapsed",
    layout="wide"
)

# Inject shared CSS
inject_shared_css()

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

tab_playground, tab_monitoring = st.tabs(["AI Playground", "Monitoring"])

with tab_playground:
    AVAILABLE_MODELS = ["mistral-small-2503", "Phi-4-mini-instruct", "gpt-4.1", "gpt-4.1-mini"]
    st.markdown('<div class="ms-section-title">Model Selection</div>', unsafe_allow_html=True)
    selected_models = [m for m in AVAILABLE_MODELS if st.checkbox(m, key=f"model_{m}")]

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

    st.markdown('<div class="ms-section-title">Prompt</div>', unsafe_allow_html=True)
    prompt = st.text_area("Enter your prompt here", height=180)

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

                    model_response = raw.choices[0].message.content
                    total_tokens = getattr(raw.usage, "total_tokens", None) or raw.usage.get("total_tokens")
                    safety = getattr(raw.choices[0], "content_filter_results", {}) or {}
                    safety_flags = sum(
                        1 for v in safety.values() if isinstance(v, dict) and v.get("filtered") is True
                    )
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

with tab_monitoring:
    st.markdown('<div class="ms-section-title">Monitoring Dashboard</div>', unsafe_allow_html=True)
    refresh_seconds = st.slider("Auto-refresh interval (seconds)", 10, 300, 60)
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = 0
    if st.button("Refresh Now"):
        st.session_state.last_refresh += 1
    try:
        monitoring_html = generate_monitoring_html(
            governance_metrics=GOVERNANCE_METRICS,
            model_costs=model_cost,
            selected_models=None,
            include_css=False  # CSS already injected globally
        )
        st.components.v1.html(monitoring_html, height=1400, scrolling=True)
    except Exception as e:
        st.error(f"Failed to render monitoring dashboard: {e}")

st.markdown("""
<div class="ms-footer">
    Azure AI Foundry Playground by Morgan Stanley<br>
</div>
""", unsafe_allow_html=True)
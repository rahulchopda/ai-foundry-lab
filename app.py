import ast
import os
import re
from typing import Any, Dict, Tuple, List

import fitz
import streamlit as st
import yaml

from model_orchestrator import ModelOrchestrator
from pii_analyzer import PIIHandler
from shared_css import inject_shared_css
from monitoring_web import render_monitoring_tab

# Initialize PII Handler
pii_handler = PIIHandler()

# --- Load Config ---
cfg: Dict = {}
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        st.warning(f"Could not load config.yaml: {e}")

model_endpoints: Dict = cfg.get("MODEL_ENDPOINTS", {})
api_key = cfg.get("API_KEY")
model_choices = cfg.get("MODEL_DEPLOYMENTS", [])
model_cost: Dict[str, float] = cfg.get("MODEL_COST", {})

SUBSCRIPTION_ID = cfg.get("SUBSCRIPTION_ID", "0b100b44-fb20-415e-b735-4594f153619b")

def extract_pdf_text(file_content) -> str:
    """Process uploaded PDF and return text content."""
    text = ""
    doc = fitz.open(stream=file_content, filetype="pdf")
    for page in doc:
        text += page.get_text()
    return text

def call_foundry_with_guardrails(endpoint: str, prompt: str, model_name: str) -> Dict:
    """Use ModelOrchestrator handler when available."""
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

def _first_choice(resp: Any) -> Any:
    if hasattr(resp, "choices"):
        choices = getattr(resp, "choices")
    elif isinstance(resp, dict):
        choices = resp.get("choices")
    else:
        choices = None
    if choices is None:
        return None
    if isinstance(choices, (list, tuple)) and choices:
        return choices[0]
    if isinstance(choices, dict):
        try:
            return next(iter(choices.values()))
        except StopIteration:
            return None
    return None

def _extract_safety_dict_from_choice(choice: Any) -> Dict:
    if choice is None:
        return {}
    if not isinstance(choice, dict):
        safety = getattr(choice, "content_filter_results", None)
    else:
        safety = choice.get("content_filter_results")
    if isinstance(safety, dict):
        return safety
    try:
        raw = str(choice)
        m = re.search(r"content_filter_results\s*=\s*(\{.*\})", raw, re.DOTALL)
        if m:
            text = m.group(1).replace("false", "False").replace("true", "True")
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    except Exception:
        pass
    return {}

def _count_flagged_and_total(safety_dict: Dict) -> Tuple[int, int, List[str]]:
    flagged = 0
    total = 0
    flagged_names: List[str] = []
    if not isinstance(safety_dict, dict):
        return 0, 0, []
    for k, v in safety_dict.items():
        if isinstance(v, dict) and "filtered" in v:
            total += 1
            try:
                if v.get("filtered") is True:
                    flagged += 1
                    flagged_names.append(k)
            except Exception:
                if str(v.get("filtered")).lower() == "true":
                    flagged += 1
                    flagged_names.append(k)
    return flagged, total, flagged_names

def parse_raw_response(raw_response):
    result = {"model_response": "No response", "total_tokens": None, "safety_flags": "N/A"}
    if isinstance(raw_response, dict):
        if raw_response.get("content") is None and "error" in raw_response:
            result["model_response"] = "⚠️ Response filtered or error"
        return result
    if hasattr(raw_response, "choices"):
        try:
            if raw_response.choices and hasattr(raw_response.choices[0], "message"):
                result["model_response"] = raw_response.choices[0].message.content or "No content"
        except Exception:
            result["model_response"] = "⚠️ Failed to extract message"
        if hasattr(raw_response, "usage") and raw_response.usage:
            result["total_tokens"] = getattr(raw_response.usage, "total_tokens", None)
        result["safety_flags"] = "N/A"
        return result
    result["model_response"] = "⚠️ Unknown response type"
    return result

# Streamlit Page Setup
st.set_page_config(
    page_title="Azure AI Foundry Playground",
    initial_sidebar_state="collapsed",
    layout="wide"
)

# Inject shared styling (single source of truth)
inject_shared_css()

# Header
st.markdown("""
<div class="ms-header">
    <img src="https://www.morganstanley.com/etc/designs/mscorporate/clientlibs/mscorporate/resources/images/ms-logo.svg"
         class="ms-logo" alt="Morgan Stanley Logo" />
    <h1 style="margin-bottom:8px;font-family: 'Helvetica Neue','Segoe UI','Arial',sans-serif !important;">
        Gen AI Playground
    </h1>
    <span style="font-size:1.2rem;font-weight:400;">
        Experiment, Evaluate, Govern, and Monitor AI Models
        <span class="badge-foundry">Powered by Azure AI Foundry</span>
    </span>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_playground, tab_monitoring = st.tabs(["AI Playground", "Monitoring"])

with tab_playground:
    st.markdown("""
    <div class="ms-card">
        <h2>Model Playground</h2>
        <p>Test and compare AI models with built-in PII detection and filtering.</p>
    </div>
    """, unsafe_allow_html=True)

    AVAILABLE_MODELS = ["mistral-small-2503", "Phi-4-mini-instruct", "gpt-4.1", "model-router"]
    st.markdown('<div class="ms-section-title">Model Selection</div>', unsafe_allow_html=True)
    cols = st.columns(len(AVAILABLE_MODELS))
    selected_models: List[str] = []
    for i, m in enumerate(AVAILABLE_MODELS):
        with cols[i]:
            if st.checkbox(m, key=f"model_{m}"):
                selected_models.append(m)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="ms-section-title">Input Data</div>', unsafe_allow_html=True)
        input_type = st.radio("Select input type", ["Text", "Document Upload"], horizontal=True)
        run_pii = st.checkbox("Detect and redact sensitive information (PII)")

        if input_type == "Text":
            input_text = st.text_area("Enter your input text here", height=180)
            doc_data = input_text
            doc_name = "Text Input"
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

    with col2:
        if run_pii and doc_data:
            try:
                with st.spinner("Detecting sensitive information..."):
                    pii_result = pii_handler.analyze_text(doc_data)
                if pii_result.get("success"):
                    entities = pii_result.get("entities") or []
                    if entities:
                        with st.expander("View Detected Sensitive Information"):
                            for entity in entities:
                                st.markdown(
                                    f"**{entity.category}**\n\n"
                                    f"- Text: `{entity.text}`\n"
                                    f"- Confidence: {getattr(entity, 'confidence_score', 0):.2f}"
                                )
                        doc_data = pii_result.get("redacted_text", doc_data)
                        with st.expander("View Redacted Input Text"):
                            st.write(doc_data)
                    else:
                        st.success("No sensitive information (PII) detected in the text")
                else:
                    st.error(f"PII detection failed: {pii_result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error during PII detection: {e}")

    st.markdown('<div class="ms-section-title">Prompt</div>', unsafe_allow_html=True)
    prompt = st.text_area("Enter your prompt here", height=180)

    st.markdown('<div class="ms-section-title">Model Execution</div>', unsafe_allow_html=True)
    if st.button("Run Models with Guardrails", type="primary", use_container_width=True):
        if not doc_data:
            st.error("Please provide input text or upload a document first.")
            st.stop()
        final_prompt = f"{prompt.strip()} {doc_data.strip()}".strip()
        with st.expander("View Final Prompt", expanded=False):
            st.write(final_prompt)
        if not selected_models:
            st.error("Please select at least one model first.")
            st.stop()

        result_cols = st.columns(len(selected_models))
        for i, model_name in enumerate(selected_models):
            with result_cols[i]:
                st.markdown(f"**{model_name}**")
                try:
                    azure_endpoint = model_endpoints.get(model_name, "").strip()
                    raw = call_foundry_with_guardrails(azure_endpoint, final_prompt, model_name)

                    if isinstance(raw, dict) and "error" in raw:
                        st.error(f"⚠️ {raw.get('error', 'Error calling model')}")
                        continue

                    # Safety
                    safety_dict = _extract_safety_dict_from_choice(_first_choice(raw))
                    flagged_count, total_cats, _flagged_names = _count_flagged_and_total(safety_dict)
                    safety_flags = f"{flagged_count}/{total_cats}" if total_cats > 0 else "0/0"

                    # Content & tokens
                    try:
                        model_response = raw.choices[0].message.content
                    except Exception:
                        model_response = "Unable to extract model response."
                    try:
                        total_tokens = getattr(raw.usage, "total_tokens", None)
                    except Exception:
                        total_tokens = None

                    st.write("Model Response:", model_response)
                    st.write("Total Tokens:", total_tokens if total_tokens is not None else "N/A")
                    st.write("Safety Flags:", safety_flags)

                    cost_per_1m = model_cost.get(model_name)
                    if cost_per_1m is not None and total_tokens is not None:
                        cost_estimate = (total_tokens / 1_000_000) * cost_per_1m
                        st.write("Cost Estimate:", f"${cost_estimate:,.6f}")
                    else:
                        st.write("Cost Estimate:", "N/A")
                except Exception as e:
                    st.error(f"Error with {model_name}: {e}")

with tab_monitoring:
    st.markdown('<div class="ms-section-title">Monitoring Dashboard</div>', unsafe_allow_html=True)
    render_monitoring_tab(
        subscription_id=SUBSCRIPTION_ID,
        governance_metrics=GOVERNANCE_METRICS,
        model_costs=model_cost,
        default_timeframe="Last7Days"
    )

st.markdown("""
<div class="ms-footer">
    Azure AI Foundry Playground by Morgan Stanley<br>
</div>
""", unsafe_allow_html=True)
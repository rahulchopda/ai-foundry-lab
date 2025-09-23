import ast
import os
import re
from typing import Any, Dict, Tuple, List, Union, Optional

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

GOVERNANCE_METRICS = {
    "Model Usage": 324,
    "Team Accesses": 18,
    "Compliance Checks": "Passed",
    "Audit Trail": "Enabled",
    "Data Residency": "US/EU",
    "Last Model Update": "2025-09-10",
}

# ---------------------- Core Utilities ---------------------- #

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
            # Normalize simple string return into expected shape
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
            parsed = ast.literal_eval(text)
            if isinstance(parsed, dict):
                return parsed
    except Exception:
        pass
    return {}

def _count_flagged_and_total(safety_dict: Dict) -> Tuple[int, int, List[str]]:
    flagged = 0
    total = 0
    names: List[str] = []
    if not isinstance(safety_dict, dict):
        return 0, 0, []
    for k, v in safety_dict.items():
        if isinstance(v, dict) and "filtered" in v:
            total += 1
            try:
                if v.get("filtered") is True:
                    flagged += 1
                    names.append(k)
            except Exception:
                if str(v.get("filtered")).lower() == "true":
                    flagged += 1
                    names.append(k)
    return flagged, total, names

# ---------------------- Error Parsing & Safety Table ---------------------- #

def _safe_literal_eval(text: str):
    try:
        return ast.literal_eval(text)
    except Exception:
        return None

def _deep_find_content_filter_result(obj) -> Dict:
    if isinstance(obj, dict):
        if "content_filter_result" in obj and isinstance(obj["content_filter_result"], dict):
            return obj["content_filter_result"]
        for v in obj.values():
            found = _deep_find_content_filter_result(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_content_filter_result(item)
            if found:
                return found
    return {}

def _deep_find_error_message(obj) -> Optional[str]:
    if isinstance(obj, dict):
        if "message" in obj and isinstance(obj["message"], str):
            return obj["message"]
        for v in obj.values():
            found = _deep_find_error_message(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_error_message(item)
            if found:
                return found
    return None

def parse_error_payload(error_str: str) -> Tuple[str, Dict]:
    """
    Returns (concise_message, content_filter_result_dict).
    """
    if not isinstance(error_str, str):
        return ("Model call failed.", {})
    if "content_filter_result" not in error_str and "message" not in error_str:
        return (error_str.split("\n")[0][:500], {})

    first = error_str.find("{")
    last = error_str.rfind("}")
    if first == -1 or last == -1:
        return (error_str[:500], {})

    blob = error_str[first:last+1]
    normalized = (blob
                  .replace("true", "True")
                  .replace("false", "False")
                  .replace("null", "None"))
    parsed = _safe_literal_eval(normalized)
    if not isinstance(parsed, (dict, list)):
        return (error_str[:500], {})

    message = _deep_find_error_message(parsed) or "Model response filtered."
    cfr = _deep_find_content_filter_result(parsed)
    return (message, cfr if isinstance(cfr, dict) else {})

def render_content_filter_table(content_filter_result: Dict):
    """
    Renders the safety table with styling aligned to the cost metrics 'Recent Days' table.
    """
    if not content_filter_result:
        return

    keys = sorted(content_filter_result.keys())
    rows: List[str] = []
    for idx, attr in enumerate(keys):
        data = content_filter_result.get(attr)
        if not isinstance(data, dict):
            continue
        filtered_val = data.get("filtered")
        severity_val = data.get("severity", "-")
        filtered_display = "True" if filtered_val else "False"
        filtered_class = "ms-safety-flag-true" if filtered_val else "ms-safety-flag-false"
        # Build row without leading indentation
        rows.append(
            "<tr>"
            f"<td style='font-weight:600;color:#002855;'>{attr}</td>"
            f"<td class='{filtered_class}' style='text-align:left;'>{filtered_display}</td>"
            f"<td style='text-align:left;'>{severity_val}</td>"
            "</tr>"
        )

    table_html = (
        "<div class='ms-safety-table-wrapper'>"
        "<div style='margin-top:0.5rem;font-weight:600;font-size:0.72rem;color:#0051a8;'>Safety / Content Filter Details</div>"
        "<table class='ms-safety-table'>"
        "<thead>"
        "<tr>"
        "<th>Attribute</th>"
        "<th>Filtered</th>"
        "<th>Severity</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)

# ---------------------- UI Setup ---------------------- #

st.set_page_config(
    page_title="Azure AI Foundry Playground",
    initial_sidebar_state="collapsed",
    layout="wide"
)

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
    model_cols = st.columns(len(AVAILABLE_MODELS))
    selected_models: List[str] = []
    for i, m in enumerate(AVAILABLE_MODELS):
        with model_cols[i]:
            if st.checkbox(m, key=m):
                selected_models.append(m)

    col1, col2 = st.columns(2)

    # Input column
    with col1:
        st.markdown('<div class="ms-section-title">Input Data</div>', unsafe_allow_html=True)
        input_type = st.radio("Select input type", ["Text", "Document Upload"], horizontal=True)
        run_pii = st.checkbox("Detect and redact sensitive information (PII)")

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

    # PII detection column
    with col2:
        if run_pii and doc_data:
            try:
                with st.spinner("Detecting sensitive information..."):
                    pii_result = pii_handler.analyze_text(doc_data)
                    if pii_result["success"]:
                        if pii_result["entities"]:
                            with st.expander("View Detected Sensitive Information"):
                                for entity in pii_result["entities"]:
                                    st.markdown(f"""
                                        **{entity.category}** found:
                                        - Text: `{entity.text}`
                                        - Confidence: {entity.confidence_score:.2f}
                                    """)
                            doc_data = pii_result["redacted_text"]
                            with st.expander("View redacted Input Text", expanded=False):
                                st.write(doc_data)
                        else:
                            st.success("No sensitive information (PII) detected in the text")
                    else:
                        st.error(f"PII detection failed: {pii_result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error during PII detection: {str(e)}")

    # Prompt
    st.markdown('<div class="ms-section-title">Prompt</div>', unsafe_allow_html=True)
    prompt = st.text_area("Enter your prompt here", height=180)

    # Execution
    st.markdown('<div class="ms-section-title">Model Execution</div>', unsafe_allow_html=True)
    if st.button("Run Models with Guardrails", type="primary", use_container_width=True):
        if not doc_data:
            st.error("Please provide input text or upload a document first.")
            st.stop()

        full_prompt = f"{prompt} {doc_data}" if doc_data else prompt
        with st.expander("View Final Prompt", expanded=False):
            st.write(full_prompt)

        if not selected_models:
            st.error("Please select at least one model first.")
            st.stop()

        result_cols = st.columns(len(selected_models))
        for i, model_name in enumerate(selected_models):
            with result_cols[i]:
                st.markdown(f"**{model_name}**")
                try:
                    azure_endpoint = model_endpoints.get(model_name, "").strip()
                    raw = call_foundry_with_guardrails(azure_endpoint, full_prompt, model_name)

                    # Error branch: only show concise message + table
                    if isinstance(raw, dict) and "error" in raw:
                        err_message, cfr = parse_error_payload(raw.get("error", ""))
                        st.error(f"⚠️ {err_message}")
                        if cfr:
                            render_content_filter_table(cfr)
                        continue  # Skip normal metrics

                    # Success branch
                    safety_dict = _extract_safety_dict_from_choice(_first_choice(raw))
                    flagged_count, total_cats, _ = _count_flagged_and_total(safety_dict)
                    safety_flags = f"{flagged_count}/{total_cats}" if total_cats > 0 else "0/0"
                    model_response = raw.choices[0].message.content
                    total_tokens = getattr(getattr(raw, "usage", None), "total_tokens", None)

                    cost_estimate = None
                    if total_tokens is not None:
                        mc_value = cfg.get("MODEL_COST", {}).get(model_name)
                        if mc_value is not None:
                            cost_estimate = (total_tokens / 1_000_000) * mc_value

                    st.write("Model Response: ", model_response)
                    st.write("Total Tokens: ", total_tokens)
                    st.write("Safety Flags: ", safety_flags)
                    if cost_estimate is not None:
                        st.write("Cost Estimate: ", round(cost_estimate, 6))

                except Exception as e:
                    st.error(f"Unexpected error with {model_name}: {e}")

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
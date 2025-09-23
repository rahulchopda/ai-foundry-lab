import streamlit as st
import json
import os
import time
import yaml
from typing import Any, Dict, Tuple, List, Union
import fitz
from azure.identity import DefaultAzureCredential
from model_orchestrator import ModelOrchestrator
from pii_analyzer import PIIHandler  # Add this import
import re
import ast

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
        # Display results
        
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

def _first_choice(resp: Any) -> Any:
    """Return the first choice object/dict if present, else None."""
    # SDK object
    if hasattr(resp, "choices"):
        choices = getattr(resp, "choices")
    elif isinstance(resp, dict):
        choices = resp.get("choices")
    else:
        choices = None

    if choices is None:
        return None

    # choices might be a list-like
    if isinstance(choices, (list, tuple)) and len(choices) > 0:
        return choices[0]
    # fallback: single dict
    if isinstance(choices, dict):
        # pick first value
        try:
            return next(iter(choices.values()))
        except StopIteration:
            return None
    return None

def _get_message_content(choice: Any) -> str:
    """Extract content from choice irrespective of dict/object shape."""
    if choice is None:
        return ""
    # object style: choice.message.content
    msg = getattr(choice, "message", None) if not isinstance(choice, dict) else choice.get("message")
    if msg:
        # msg might be object or dict
        return getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else "") or ""
    # older style: choice.get("text") or choice.text
    if isinstance(choice, dict):
        return choice.get("text") or choice.get("content") or ""
    return getattr(choice, "text", "") or getattr(choice, "content", "")

def _get_total_tokens(resp: Any) -> int:
    """Extract total_tokens from response object/dict or return -1."""
    usage = getattr(resp, "usage", None) if not isinstance(resp, dict) else resp.get("usage")
    if usage:
        # usage may be object with attribute total_tokens or dict
        if isinstance(usage, dict):
            return int(usage.get("total_tokens", -1)) if usage.get("total_tokens") is not None else -1
        return int(getattr(usage, "total_tokens", -1))
    # if not found, try regex on string form
    try:
        raw = str(resp)
        m = re.search(r"total_tokens\s*=\s*(\d+)", raw)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return -1

def _extract_safety_dict_from_choice(choice: Any) -> Dict:
    """Return the content_filter_results dict if present, else {}."""
    if choice is None:
        return {}
    # object attribute or dict key
    safety = None
    if not isinstance(choice, dict):
        safety = getattr(choice, "content_filter_results", None)
    else:
        safety = choice.get("content_filter_results")
    # sometimes the field appears after the message in the raw string (rare) — handled by raw fallback below
    if isinstance(safety, dict):
        return safety
    # try to fallback to searching raw string of the choice
    try:
        raw = str(choice)
        m = re.search(r"content_filter_results\s*=\s*(\{.*\})", raw, re.DOTALL)
        if m:
            text = m.group(1)
            # make booleans Pythonic
            text_fixed = text.replace("false", "False").replace("true", "True")
            try:
                parsed = ast.literal_eval(text_fixed)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    except Exception:
        pass
    return {}

def _count_flagged_and_total(safety_dict: Dict) -> Tuple[int, int, List[str]]:
    """
    Count how many top-level categories have 'filtered'==True,
    how many categories have a 'filtered' key (total), and return list of flagged category names.
    """
    flagged = 0
    total = 0
    flagged_names: List[str] = []
    if not isinstance(safety_dict, dict):
        return 0, 0, []

    # top-level keys only (user requested 3/5 style where denominator is count of categories)
    for k, v in safety_dict.items():
        if isinstance(v, dict) and "filtered" in v:
            total += 1
            try:
                if v.get("filtered") is True:
                    flagged += 1
                    flagged_names.append(k)
            except Exception:
                # if value is "True"/"False" strings, handle them
                if str(v.get("filtered")).lower() == "true":
                    flagged += 1
                    flagged_names.append(k)
    return flagged, total, flagged_names

def parse_raw_response(raw_response):
    """
    Handles both ChatCompletion objects (success) and dict error responses.
    Returns: dict with model_response (str), total_tokens (int|None), safety_flags (str)
    """
    result = {
        "model_response": "No response",
        "total_tokens": None,
        "safety_flags": "N/A"
    }

    # -----------------------
    # Case 1: Error dict
    # -----------------------
    if isinstance(raw_response, dict):
        if raw_response.get("content") is None and "error" in raw_response:
            result["model_response"] = "⚠️ Response filtered or error"
            error_str = raw_response.get("error", "")

            # Try to extract safety flags
            import re, json
            if "content_filter_result" in error_str:
                try:
                    # Replace Python-like dict string with valid JSON
                    fixed = re.sub(r"(\w+):", r'"\1":', error_str.replace("'", '"'))
                    parsed = json.loads(fixed)
                    cfr = (
                        parsed.get("error", {})
                        .get("innererror", {})
                        .get("content_filter_result", {})
                    )
                    result["safety_flags"] = 0 # _calculate_flags(cfr)
                except Exception as e:
                    result["safety_flags"] = f"Parse failed: {e}"
        return result

    # -----------------------
    # Case 2: ChatCompletion object
    # -----------------------
    if hasattr(raw_response, "choices"):
        try:
            if raw_response.choices and hasattr(raw_response.choices[0], "message"):
                result["model_response"] = (
                    raw_response.choices[0].message.content or "No content"
                )
        except Exception:
            result["model_response"] = "⚠️ Failed to extract message"

        if hasattr(raw_response, "usage") and raw_response.usage:
            result["total_tokens"] = getattr(raw_response.usage, "total_tokens", None)

        flags = {}
        try:
            if (
                raw_response.choices
                and hasattr(raw_response.choices[0], "content_filter_results")
            ):
                cfr = raw_response.choices[0].content_filter_results
                if cfr:
                    flags.update(cfr)

            if hasattr(raw_response, "prompt_filter_results"):
                for p in raw_response.prompt_filter_results or []:
                    if isinstance(p, dict):
                        flags.update(p.get("content_filter_results", {}))
        except Exception:
            pass

        result["safety_flags"] = 0 # _calculate_flags(flags)
        return result

    # -----------------------
    # Unknown type
    # -----------------------
    result["model_response"] = "⚠️ Unknown response type"
    return result


def _calculate_flags(flags_dict):
    """Helper: count how many categories were flagged."""
    flags_total = 0
    flags_count = 0

    for _, v in flags_dict.items():
        if isinstance(v, dict) and "filtered" in v:
            flags_total += 1
            if v.get("filtered", False):
                flags_count += 1

    return f"{flags_count}/{flags_total}" if flags_total > 0 else "N/A"

# Set wide layout, remove sidebar
st.set_page_config(page_title="Azure AI Foundry Playground", initial_sidebar_state="collapsed")

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
#st.markdown('<div class="ms-section-title">Model Selection</div>', unsafe_allow_html=True)
#if model_choices:
#    selected_model = st.selectbox("Choose model:", model_choices)
#else:
#    st.warning("No models configured. Please check config.yaml")
#    selected_model = None

# Tabs for navigation
tab1, tab2 = st.tabs(["Model Playground", "Monitoring Dashboard"])
with tab1:
    st.markdown("""
    <div class="ms-card">
        <h2>Model Playground</h2>
        <p>Test and compare AI models with built-in PII detection and filtering.</p>
    </div>
    """, unsafe_allow_html=True)
    # Model Selection
    AVAILABLE_MODELS = ["mistral-small-2503", "Phi-4-mini-instruct", "gpt-4.1","model-router"]
    st.markdown('<div class="ms-section-title">Model Selection</div>', unsafe_allow_html=True)
    cols = st.columns(len(AVAILABLE_MODELS))
    selected_models = []
    for i, m in enumerate(AVAILABLE_MODELS):
        with cols[i]:
            if st.checkbox(m, key=m):
                selected_models.append(m)

    # --- Input Section ---
    col1, col2 = st.columns(2)

    with col1:
        # --- Input Text/Document ---
        st.markdown('<div class="ms-section-title">Input Data</div>', unsafe_allow_html=True)
        input_type = st.radio("Select input type", ["Text", "Document Upload"], horizontal=True)
        run_pii = st.checkbox("Detect and redact sensitive information (PII)")

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
        

    with col2:        
        # Add PII Detection option after input
        if run_pii and doc_data:        
            try:
                with st.spinner("Detecting sensitive information..."):
                    pii_result = pii_handler.analyze_text(doc_data)

                    if pii_result["success"]:
                        if pii_result["entities"]:
                            

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
                            # pii_result_box.json(pii_result
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

    # --- Run Models with Guardrails ---
    st.markdown('<div class="ms-section-title">Model Execution</div>', unsafe_allow_html=True)
    if st.button("Run Models with Guardrails", type="primary", use_container_width=True):
        if not doc_data:
            st.error("Please provide input text or upload a document first.")
            st.stop()
        
        #progress_bar = st.progress(0)
        #status_text = st.empty()
        # Prepare prompt
        if doc_data:    
            prompt = prompt + " " + doc_data
        #progress_bar.progress(50)
        #status_text.text("Calling models...")

        # Display the final prompt
        with st.expander("View Final Prompt", expanded=False):
            st.write(prompt)

        if not selected_models:
            st.error("Please select at least one model first.")
            st.stop()

        cols = st.columns(len(selected_models))  # side-by-side results
        
        for i, model_name in enumerate(selected_models):
            with cols[i]:
                st.markdown(f"**{model_name}**")
                try:
                    # Call model
                    azure_endpoint = model_endpoints.get(model_name, "").strip()
                    print(model_name, azure_endpoint, prompt, model_name)
                    raw = call_foundry_with_guardrails(
                        azure_endpoint, prompt, model_name
                    )

                    
                    # --- Content ---
                    print("raw content:", raw)
                    model_response = raw.choices[0].message.content

                    # --- Total tokens ---
                    total_tokens = raw.usage.total_tokens

                    # --- Safety flags ---
                    safety = raw.choices[0].content_filter_results
                    safety_flags = sum(1 for v in safety.values() if isinstance(v, dict) and v.get("filtered") is True)

                        
                    #model_response, total_tokens, safety_flags = parse_raw_response(raw)
                    print("model_response:", model_response)
                    print("total_tokens:", total_tokens)
                    print("safety_flags:", safety_flags)
                    #safety_flags = "safety_flags (out of "+ str(total_cats) + "): " + str(flagged_count)
                    # Cost estimation (example rates, adjust as needed)
                    cost_per_1m_tokens=cfg.get("MODEL_COST")[model_name]
                    print("cost_per_1m_tokens:", cost_per_1m_tokens)
                    #cost_per_1m_tokens = float(cost_per_1m_tokens.strip())
                    cost_estimate = (total_tokens / 1000000) * cost_per_1m_tokens 

                    #st.subheader("Model Response")
                    st.write("Model Response: ", model_response)

                    #st.subheader("Total Tokens")
                    st.write("Total Tokens: ", total_tokens)

                    #st.subheader("Safety Flags")
                    st.write("Safety Flags: ", safety_flags)

                    #st.subheader("cost estimate")
                    st.write("cost estimate: ", cost_estimate)
                except Exception as e:
                    st.error(f"Error with {model_name}: {e}") 
                    st.write("Model Response: ", model_response)

# Monitoring Section with HTML Files
#st.markdown('<div class="ms-section-title">Monitoring Dashboard</div>', unsafe_allow_html=True)
#monitoring_cols = st.columns(3)

#with monitoring_cols[0]:
#    st.markdown('<div class="ms-section-title">Model Performance Metrics</div>', unsafe_allow_html=True)
#    with open(os.path.join(os.path.dirname(__file__), "io_metrics.html"), "r", encoding="utf-8") as f:
#        st.components.v1.html(f.read(), height=400, scrolling=True)

#with monitoring_cols[1]:
#    st.markdown('<div class="ms-section-title">Request Count Over Time</div>', unsafe_allow_html=True)
#    with open(os.path.join(os.path.dirname(__file__), "request_count.html"), "r", encoding="utf-8") as f:
#        st.components.v1.html(f.read(), height=400, scrolling=True)
#
#with monitoring_cols[2]:
#    st.markdown('<div class="ms-section-title">Model Latency (ms)</div>', unsafe_allow_html=True)
#    with open(os.path.join(os.path.dirname(__file__), "latency.html"), "r", encoding="utf-8") as f:
#        st.components.v1.html(f.read(), height=400, scrolling=True)

# --- PAGE 2: Monitoring Dashboard ---
with tab2:
    st.header("Monitoring Dashboard")

    st.info("This is a placeholder. Governance metrics, request counts, and latency charts will go here.")

    cols = st.columns(3)
    with cols[0]:
        st.metric("Total Interactions", 245)
    with cols[1]:
        st.metric("Avg Latency (ms)", "320")
    with cols[2]:
        st.metric("Avg Tokens/Req", "145")

    st.markdown("More detailed charts (latency, request volume, safety events) can be embedded here.")


# Footer
st.markdown("""
<div class="ms-footer">
    Azure AI Foundry Playground by Morgan Stanley<br>
</div>
""", unsafe_allow_html=True)
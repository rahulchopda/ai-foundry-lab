import streamlit as st
import json
import os
import time
from dotenv import load_dotenv
from typing import Dict, List

# Load environment variables
load_dotenv()

# Dummy model list and governance metrics for demonstration
MODEL_OPTIONS = [
    {"name": "OpenAI GPT-4", "vendor": "OpenAI", "type": "Text", "desc": "General text generation"},
    {"name": "Azure OpenAI GPT-4o", "vendor": "Azure", "type": "Text", "desc": "Enterprise-grade generative AI"},
    {"name": "Mistral Large", "vendor": "Mistral", "type": "Text", "desc": "Open-source, advanced reasoning"},
    {"name": "Llama-3 70B", "vendor": "Meta", "type": "Text", "desc": "High-performance, open weights"},
    {"name": "Stable Diffusion XL", "vendor": "Stability", "type": "Image", "desc": "Text-to-image generation"},
]

GOVERNANCE_METRICS = {
    "Model Usage": 324,
    "Team Accesses": 18,
    "Compliance Checks": "Passed",
    "Audit Trail": "Enabled",
    "Data Residency": "US/EU",
    "Last Model Update": "2025-09-10",
}

# Set wide layout, remove sidebar
st.set_page_config(page_title="Gen AI Model Playground", layout="wide", initial_sidebar_state="collapsed")

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
    <h1 style="margin-bottom:8px;font-family: 'Helvetica Neue', 'Segoe UI', 'Arial', sans-serif !important;">Gen AI Model Playground</h1>
    <span style="font-size:1.2rem;font-weight:400;">
        Experiment, Evaluate, Compare <span class="badge-foundry">Azure AI Foundry</span>
    </span>
</div>
""", unsafe_allow_html=True)

# Main Playground Card
st.markdown("""
<div class="ms-card">
    <div class="ms-section-title">Gen AI Model Evaluation Playground</div>
    <div style="font-size:1.15rem;color:#002855;">
        Test and compare Gen AI models. Upload docs or paste text. Analyze model output, see statistics, and review governance metrics — all in one place.
    </div>
    <div style="margin-top:1rem;">
        <span class="badge bg-primary" style="margin-right:0.7em;"><i class="bi bi-gear bootstrap-icon"></i>Multi-vendor Model Selection</span>
        <span class="badge bg-secondary" style="margin-right:0.7em;"><i class="bi bi-file-earmark bootstrap-icon"></i>Document/Text Upload & Paste</span>
        <span class="badge bg-success" style="margin-right:0.7em;"><i class="bi bi-bar-chart bootstrap-icon"></i>Model Metrics</span>
        <span class="badge bg-info text-dark"><i class="bi bi-shield-check bootstrap-icon"></i>AI Governance</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Model selection ---
st.markdown('<div class="ms-section-title">Select Gen AI Model</div>', unsafe_allow_html=True)
model_names = [f"{m['name']} ({m['vendor']})" for m in MODEL_OPTIONS]
selected_model_idx = st.selectbox("Choose a Gen AI model", options=list(range(len(model_names))), format_func=lambda x: model_names[x])
selected_model = MODEL_OPTIONS[selected_model_idx]

with st.expander("Model Details", expanded=False):
    st.markdown(
        f"<span style='font-size:1.1em;'><b>{selected_model['name']}</b> from <b>{selected_model['vendor']}</b></span><br>"
        f"<span style='color:#0051a8;'>Type:</span> {selected_model['type']}<br>"
        f"<span style='color:#0051a8;'>Description:</span> {selected_model['desc']}",
        unsafe_allow_html=True
    )
    st.progress(65 if selected_model['vendor'] == "Azure" else 40)

# --- Document/Text Upload/Paste ---
st.markdown('<div class="ms-section-title">Input Data</div>', unsafe_allow_html=True)
input_type = st.radio("Select input type", ["Text Paste", "Document Upload"], horizontal=True)

if input_type == "Text Paste":
    input_text = st.text_area("Paste your text here", height=180)
    doc_data = input_text
    doc_name = "Pasted Text"
elif input_type == "Document Upload":
    uploaded_file = st.file_uploader("Upload a document (PDF, TXT, DOCX)", type=["pdf", "txt", "docx"])
    doc_data = None
    doc_name = None
    if uploaded_file is not None:
        doc_name = uploaded_file.name
        file_size = len(uploaded_file.getvalue()) / 1024  # KB
        st.markdown(
            f'<div class="ms-success">File uploaded: <b>{doc_name}</b> ({file_size:.1f} KB)</div>',
            unsafe_allow_html=True
        )
        if uploaded_file.type == "text/plain":
            doc_data = uploaded_file.read().decode("utf-8")
        else:
            doc_data = f"Binary content of {doc_name} ({uploaded_file.type})"

# --- Advanced Foundry Widgets (simulated) ---
st.markdown('<div class="ms-section-title">Azure AI Foundry Advanced Widgets</div>', unsafe_allow_html=True)
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric(label="Compliance Score", value="98.7%", delta="+0.2%")
    st.progress(98)
with col_b:
    st.metric(label="Audit Trail Coverage", value="100%", delta=None)
    st.progress(100)
with col_c:
    st.metric(label="Model Drift", value="Low", delta="-0.1%")
    st.progress(30)

with st.expander("Governance & Model Access", expanded=False):
    st.markdown(f"<span style='color:#0051a8;'>Team Accesses:</span> {GOVERNANCE_METRICS['Team Accesses']}<br>"
                f"<span style='color:#0051a8;'>Data Residency:</span> {GOVERNANCE_METRICS['Data Residency']}<br>"
                f"<span style='color:#0051a8;'>Last Model Update:</span> {GOVERNANCE_METRICS['Last Model Update']}",
                unsafe_allow_html=True)

# --- Model Execution ---
st.markdown('<div class="ms-section-title">Run Model & View Results</div>', unsafe_allow_html=True)
run_btn = st.button("Run Model", type="primary", use_container_width=True)

if run_btn and doc_data:
    exec_start = time.time()
    time.sleep(0.8)  # Simulate latency
    exec_end = time.time()
    latency = exec_end - exec_start
    token_usage = len(doc_data.split()) if isinstance(doc_data, str) else 0
    model_stats = {
        "Input Length (tokens)": token_usage,
        "Execution Time (s)": f"{latency:.2f}",
        "Model Invocations": 1,
        "Status": "Success"
    }
    model_output = f"Demo output from {selected_model['name']} on input: {doc_name or 'Text'}\n---\n{doc_data[:400]}{'...' if isinstance(doc_data, str) and len(doc_data)>400 else ''}"

    # --- Results Card ---
    st.markdown('<div class="ms-card">', unsafe_allow_html=True)
    st.markdown(f"<div class='ms-section-title' style='font-size:1.2rem;'>Model Output</div>", unsafe_allow_html=True)
    st.code(model_output, language="markdown")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Model statistics ---
    st.markdown('<div class="ms-card">', unsafe_allow_html=True)
    st.markdown(f"<div class='ms-section-title' style='font-size:1.2rem;'>Model Statistics</div>", unsafe_allow_html=True)
    stats_cols = st.columns(len(model_stats))
    for idx, (k, v) in enumerate(model_stats.items()):
        with stats_cols[idx]:
            st.markdown(f"<span style='color:#0051a8;font-weight:500;'>{k}</span><br><span style='font-size:1.15em;'>{v}</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Governance metrics ---
    st.markdown('<div class="ms-card">', unsafe_allow_html=True)
    st.markdown(f"<div class='ms-section-title' style='font-size:1.2rem;'>Azure AI Foundry Governance Metrics</div>", unsafe_allow_html=True)
    gov_cols = st.columns(len(GOVERNANCE_METRICS))
    for idx, (k, v) in enumerate(GOVERNANCE_METRICS.items()):
        with gov_cols[idx]:
            st.markdown(f"<span style='color:#0051a8;font-weight:500;'>{k}</span><br><span style='font-size:1.05em;'>{v}</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Select a model and provide input text or upload a document to run the playground.")

# Morgan Stanley-style footer
st.markdown("""
<div class="ms-footer">
    Gen AI Model Playground by Morgan Stanley AI Foundry<br>
    Empowering teams to evaluate, govern, and innovate with Generative AI.
</div>
""", unsafe_allow_html=True)
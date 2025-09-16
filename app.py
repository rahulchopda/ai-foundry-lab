import streamlit as st
import json
import os
import time
from dotenv import load_dotenv
from typing import Dict, List

# Load environment variables
load_dotenv()

# Import from your local modules
try:
    import importlib.util

    # Import docAI-pdf.py
    spec1 = importlib.util.spec_from_file_location("pdfDocumentAi", "mistral-document-ai-pdf.py")
    pdfDocumentAi = importlib.util.module_from_spec(spec1)
    spec1.loader.exec_module(pdfDocumentAi)
    process_pdf_with_mistral = pdfDocumentAi.process_pdf_with_mistral

    # Import parse-content-pdf.py
    spec2 = importlib.util.spec_from_file_location("parse_content_pdf", "parse-content-pdf.py")
    parse_content_pdf = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(parse_content_pdf)
    extract_recipe_components = parse_content_pdf.extract_recipe_components
    create_shopping_list = parse_content_pdf.create_shopping_list
    extract_cooking_temps_and_times = parse_content_pdf.extract_cooking_temps_and_times
    generate_summary = parse_content_pdf.generate_summary

except ImportError as e:
    st.error(f"❌ Error importing modules: {e}")
    st.stop()
except Exception as e:
    st.error(f"❌ Error loading modules: {e}")
    st.stop()

# Morgan Stanley theme CSS
st.markdown("""
<style>
    body, .main, .block-container {
        font-family: 'MS Helvetica', 'Segoe UI', 'Arial', sans-serif !important;
        background-color: #f7f8fa !important;
        color: #1a1a1a !important;
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
        font-size: 1.7rem;
        color: #0051a8;
        font-weight: 600;
        margin-bottom: 1rem;
        letter-spacing: 1.5px;
        font-family: 'MS Helvetica', 'Segoe UI', 'Arial', sans-serif !important;
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
    .ms-shopping-item {
        font-size: 1.05rem;
        margin: 0.5rem 0;
        padding: 0.5rem 1rem;
        background: #f7f8fa;
        border-left: 4px solid #00b294;
        border-radius: 5px;
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
    .ms-sidebar-header {
        font-size: 1.5rem;
        color: #0051a8;
        font-weight: bold;
        margin-bottom: 1rem;
        letter-spacing: 1px;
    }
    .ms-resource-link {
        color: #0051a8 !important;
        font-weight: 500;
        text-decoration: none !important;
        margin-left: 8px;
    }
    .ms-divider {
        border: none;
        border-top: 1px solid #eaecef;
        margin: 1rem 0;
    }
    /* Buttons */
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
    /* Expander */
    .stExpander {
        border: 1px solid #eaecef !important;
        background: #f7f8fa !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# Morgan Stanley-style header
st.markdown("""
<div class="ms-header">
    <img src="https://www.morganstanley.com/etc/designs/mscorporate/clientlibs/mscorporate/resources/images/ms-logo.svg" class="ms-logo" alt="Morgan Stanley Logo" />
    <h1 style="margin-bottom:8px;font-family: 'MS Helvetica', 'Segoe UI', 'Arial', sans-serif !important;">Recipe PDF to Shopping List Demo</h1>
    <span style="font-size:1.2rem;font-weight:400;">Powered by Mistral Document AI & Morgan Stanley AI Foundry</span>
</div>
""", unsafe_allow_html=True)

# Sidebar for MS-style info
with st.sidebar:
    st.markdown('<div class="ms-sidebar-header">🧭 Demo Guide</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:1.05rem;">
    <b>This demo showcases:</b>
    <ul style="margin-top:0.5rem;">
        <li>📄 <b>PDF Document AI</b> — Extract text from recipe PDFs using Mistral Document AI</li>
        <li>🧠 <b>Smart Parsing</b> — Parse ingredients, steps, and cooking parameters</li>
        <li>🛒 <b>Shopping List Generation</b> — Clean, actionable lists for your groceries</li>
        <li>📊 <b>Recipe Analysis</b> — Cooking temps, times, and step breakdowns</li>
    </ul>
    <b>Demo Flow:</b>
    <ol>
        <li>Upload a recipe PDF</li>
        <li>AI extracts and structures the content</li>
        <li>Get a shopping list & cooking info instantly</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<hr class="ms-divider"/>', unsafe_allow_html=True)
    st.markdown("""
    <b>Resources:</b>
    <ul>
        <li><a href="https://aka.ms/insideAIF" class="ms-resource-link">Watch Demo</a></li>
        <li><a href="https://aka.ms/insideAIF" class="ms-resource-link">View Code</a></li>
        <li><a href="https://aka.ms/insideAIF" class="ms-resource-link">Join Discord</a></li>
    </ul>
    """, unsafe_allow_html=True)

# Main MS-style card
st.markdown("""
<div class="ms-card">
    <div class="ms-section-title">🚀 AI-Powered Recipe Intelligence</div>
    <div style="font-size:1.15rem;color:#002855;">
        Upload a recipe PDF and let AI deliver a structured shopping list & cooking guide—styled in the spirit of Morgan Stanley digital products.
    </div>
</div>
""", unsafe_allow_html=True)

# File upload section
st.markdown('<div class="ms-section-title">📤 Step 1: Upload Your Recipe PDF</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Choose a PDF file containing a recipe",
    type="pdf",
    help="Upload any recipe PDF—cookbooks, blogs, recipe cards"
)

if uploaded_file is not None:
    file_size = len(uploaded_file.getvalue()) / 1024  # KB
    st.markdown(
        f'<div class="ms-success">✅ File uploaded: <b>{uploaded_file.name}</b> ({file_size:.1f} KB)</div>',
        unsafe_allow_html=True
    )

    # Save uploaded file
    temp_file_path = "temp_recipe.pdf"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Process button, MS style
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        process_button = st.button("Process Recipe with AI", type="primary", use_container_width=True)

    if process_button:
        st.markdown('<div class="ms-section-title">⚙️ Step 2: AI Processing</div>', unsafe_allow_html=True)

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔄 Step 1/3: Sending PDF to Mistral Document AI...")
            progress_bar.progress(10)

            import io
            import contextlib

            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                result = process_pdf_with_mistral(temp_file_path)

            if result is None:
                st.error("❌ Failed to process PDF. Please check your API key and try again.")
                st.stop()

            progress_bar.progress(40)
            status_text.text("✅ Document AI processing complete!")

            status_text.text("🔄 Step 2/3: Extracting recipe components...")
            progress_bar.progress(60)

            full_content = ""
            for page in result['pages']:
                full_content += page['markdown'] + "\n\n"

            f2 = io.StringIO()
            with contextlib.redirect_stdout(f2):
                recipe = extract_recipe_components(full_content)
                shopping_list = create_shopping_list(recipe)
                temps_times = extract_cooking_temps_and_times(full_content)

            progress_bar.progress(80)

            status_text.text("🔄 Step 3/3: Generating summary and results...")
            summary = generate_summary(recipe, temps_times)

            progress_bar.progress(100)
            status_text.text("🎉 Processing complete!")

            time.sleep(1)
            progress_bar.empty()
            status_text.empty()

            # Results section: Morgan Stanley Card
            st.markdown('<hr class="ms-divider"/>', unsafe_allow_html=True)
            st.markdown('<div class="ms-section-title">📊 Step 3: Results</div>', unsafe_allow_html=True)

            # Summary card
            st.markdown(f"""
            <div class="ms-success">
                <h4 style="margin-bottom:0.5rem;">🍽️ Recipe Summary: <span style="color:#0051a8;">{recipe['title']}</span></h4>
                <ul style="list-style:none;padding-left:0;margin-top:0.2rem;">
                    <li><b>{recipe['ingredient_count']}</b> ingredients needed</li>
                    <li><b>{recipe['step_count']}</b> cooking steps</li>
                    <li><b>Cooking temperatures:</b> {', '.join(temps_times['temperatures']) if temps_times['temperatures'] else 'None detected'}</li>
                    <li><b>Estimated times:</b> {', '.join(temps_times['cooking_times']) if temps_times['cooking_times'] else 'None detected'}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown('<div class="ms-section-title" style="font-size:1.2rem;">🛒 Shopping List</div>', unsafe_allow_html=True)
                st.markdown('<span style="color:#002855;">Clean, actionable shopping list:</span>', unsafe_allow_html=True)

                if shopping_list:
                    for i, item in enumerate(shopping_list, 1):
                        st.markdown(f"""
                        <div class="ms-shopping-item">
                            <b>{i}.</b> {item}
                        </div>
                        """, unsafe_allow_html=True)
                    shopping_list_text = "\n".join([f"{i}. {item}" for i, item in enumerate(shopping_list, 1)])
                    st.download_button(
                        label="📥 Download Shopping List",
                        data=shopping_list_text,
                        file_name=f"shopping_list_{recipe['title'].replace(' ', '_')}.txt",
                        mime="text/plain"
                    )
                else:
                    st.warning("No shopping list items extracted")

            with col2:
                st.markdown('<div class="ms-section-title" style="font-size:1.2rem;">🌡️ Cooking Parameters</div>', unsafe_allow_html=True)

                if temps_times['temperatures']:
                    st.markdown("**🌡️ Temperatures:**")
                    for temp in temps_times['temperatures']:
                        st.write(f"• {temp}")
                else:
                    st.write("• No temperatures detected")

                if temps_times['cooking_times']:
                    st.markdown("**⏰ Cooking Times:**")
                    for cooking_time in temps_times['cooking_times']:
                        st.write(f"• {cooking_time}")
                else:
                    st.write("• No cooking times detected")

                st.markdown("**📊 Processing Stats:**")
                st.write(f"• Pages processed: {result['usage_info']['pages_processed']}")
                st.write(f"• Document size: {result['usage_info']['doc_size_bytes']:,} bytes")

            # Detailed ingredients and instructions
            with st.expander("📖 Detailed Ingredients & Instructions", expanded=False):
                col_ing, col_inst = st.columns([1, 1])
                with col_ing:
                    st.markdown('<div class="ms-section-title" style="font-size:1.1rem;">🥗 Ingredients</div>', unsafe_allow_html=True)
                    for ingredient in recipe['ingredients']:
                        st.write(f"• {ingredient}")
                with col_inst:
                    st.markdown('<div class="ms-section-title" style="font-size:1.1rem;">👨‍🍳 Cooking Steps</div>', unsafe_allow_html=True)
                    for i, step in enumerate(recipe['instructions'], 1):
                        clean_step = step.replace('\n', ' ').strip()
                        st.write(f"{i}. {clean_step}")

            # Raw extracted content
            with st.expander("📄 Raw Extracted Content", expanded=False):
                st.markdown('<span style="color:#0051a8;">This is the raw markdown extracted by Document AI:</span>', unsafe_allow_html=True)
                st.code(full_content, language="markdown")

            output_data = {
                "recipe": recipe,
                "cooking_info": temps_times,
                "shopping_list": shopping_list,
                "original_pages": len(result['pages']),
                "document_size": result['usage_info']['doc_size_bytes']
            }

            st.download_button(
                label="💾 Download Structured Recipe Data (JSON)",
                data=json.dumps(output_data, indent=2, ensure_ascii=False),
                file_name=f"recipe_data_{recipe['title'].replace(' ', '_')}.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"❌ An error occurred during processing: {str(e)}")
            st.exception(e)

        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

else:
    st.info("👆 Please upload a PDF file to begin the demo")

    st.markdown('<hr class="ms-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="ms-section-title">🎯 How It Works</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="ms-card" style="padding:1rem 1rem 0.5rem 1rem;">
        <b>📄 Step 1: Upload</b>
        <ul>
            <li>Cookbook pages</li>
            <li>Recipe cards</li>
            <li>Blog screenshots</li>
            <li>Handwritten recipes</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="ms-card" style="padding:1rem 1rem 0.5rem 1rem;">
        <b>🧠 Step 2: AI Processing</b>
        <ul>
            <li>Mistral Document AI extracts text</li>
            <li>Preserves formatting</li>
            <li>Handles complex layouts</li>
            <li>Recognizes structure</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="ms-card" style="padding:1rem 1rem 0.5rem 1rem;">
        <b>🛒 Step 3: Smart Output</b>
        <ul>
            <li>Clean shopping list</li>
            <li>Cooking parameters</li>
            <li>Step-by-step instructions</li>
            <li>Downloadable formats</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

# Morgan Stanley-style footer
st.markdown("""
<div class="ms-footer">
    <p>🤖 Powered by Mistral Document AI & Morgan Stanley AI Foundry</p>
    <p>Transform any recipe PDF into actionable cooking data—Morgan Stanley style.</p>
</div>
""", unsafe_allow_html=True)
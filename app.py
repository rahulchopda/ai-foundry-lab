import streamlit as st
import json
import os
import time
from typing import Dict, List

# Import from your local modules
try:
    import importlib.util
    
    # Import docAI-pdf.py
    spec1 = importlib.util.spec_from_file_location("docAI_pdf", "docAI-pdf.py")
    docAI_pdf = importlib.util.module_from_spec(spec1)
    spec1.loader.exec_module(docAI_pdf)
    process_pdf_with_mistral = docAI_pdf.process_pdf_with_mistral
    
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

# Configure Streamlit page
st.set_page_config(
    page_title="Recipe",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    .demo-section {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .shopping-item {
        font-size: 1.1rem;
        margin: 0.5rem 0;
        padding: 0.3rem;
        background-color: #ffffff;
        border-left: 4px solid #4CAF50;
        padding-left: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar for demo info
with st.sidebar:
    st.header("🎯 Demo Information")
    st.markdown("""
    **This demo showcases:**
    
    - 📄 **PDF Document AI** - Extract text from recipe PDFs using Mistral Document AI
    - 🧠 **Smart Processing** - Parse ingredients, instructions, and cooking parameters
    - 🛒 **Shopping List Generation** - Create clean, actionable shopping lists
    - 📊 **Recipe Analysis** - Extract cooking temps, times, and steps

    **Demo Flow:**
    1. Upload a recipe PDF
    2. AI extracts and structures the content
    3. Get an instant shopping list + cooking info
    """)
    
    st.markdown("---")
    st.markdown("**Resources**")
    st.markdown("• [Watch Demo](https://aka.ms/insideAIF)")
    st.markdown("• [View Code](https://aka.ms/insideAIF)")
    st.markdown("• [Join Discord](https://aka.ms/insideAIF)")

# Main interface
st.markdown('<h1 class="main-header">🍽️ Recipe PDF to Shopping List Demo</h1>', unsafe_allow_html=True)

st.markdown("""
<div class="demo-section">
<h3>🚀 AI-Powered Recipe Processing</h3>
Upload a recipe PDF and watch AI transform it into a structured shopping list and cooking guide!
</div>
""", unsafe_allow_html=True)

# File upload section
st.subheader("📤 Step 1: Upload Your Recipe PDF")
uploaded_file = st.file_uploader(
    "Choose a PDF file containing a recipe", 
    type="pdf",
    help="Upload any recipe PDF - from cookbooks, blogs, or recipe cards"
)

if uploaded_file is not None:
    # Display file info
    file_size = len(uploaded_file.getvalue()) / 1024  # KB
    st.success(f"✅ File uploaded: **{uploaded_file.name}** ({file_size:.1f} KB)")
    
    # Save uploaded file
    temp_file_path = "temp_recipe.pdf"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Process button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        process_button = st.button("🚀 Process Recipe with AI", type="primary", use_container_width=True)
    
    if process_button:
        # Processing section
        st.subheader("⚙️ Step 2: AI Processing")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Document AI Processing
            status_text.text("🔄 Step 1/3: Sending PDF to Mistral Document AI...")
            progress_bar.progress(10)
            
            # Capture console output for demo purposes
            import io
            import contextlib
            
            # Redirect stdout to capture print statements
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                result = process_pdf_with_mistral(temp_file_path)
            
            if result is None:
                st.error("❌ Failed to process PDF. Please check your API key and try again.")
                st.stop()
            
            progress_bar.progress(40)
            status_text.text("✅ Document AI processing complete!")
            
            # Step 2: Extract recipe data
            status_text.text("🔄 Step 2/3: Extracting recipe components...")
            progress_bar.progress(60)
            
            # Combine all page content
            full_content = ""
            for page in result['pages']:
                full_content += page['markdown'] + "\n\n"
            
            # Extract structured data
            f2 = io.StringIO()
            with contextlib.redirect_stdout(f2):
                recipe = extract_recipe_components(full_content)
                shopping_list = create_shopping_list(recipe)
                temps_times = extract_cooking_temps_and_times(full_content)
            
            progress_bar.progress(80)
            
            # Step 3: Generate summary
            status_text.text("🔄 Step 3/3: Generating summary and results...")
            summary = generate_summary(recipe, temps_times)
            
            progress_bar.progress(100)
            status_text.text("🎉 Processing complete!")
            
            time.sleep(1)  # Brief pause for effect
            progress_bar.empty()
            status_text.empty()
            
            # Results section
            st.markdown("---")
            st.subheader("📊 Step 3: Results")
            
            # Summary card
            st.markdown(f"""
            <div class="success-box">
            <h4>🍽️ Recipe Summary: {recipe['title']}</h4>
            <ul>
                <li><strong>{recipe['ingredient_count']}</strong> ingredients needed</li>
                <li><strong>{recipe['step_count']}</strong> cooking steps</li>
                <li><strong>Cooking temperatures:</strong> {', '.join(temps_times['temperatures']) if temps_times['temperatures'] else 'None detected'}</li>
                <li><strong>Estimated times:</strong> {', '.join(temps_times['cooking_times']) if temps_times['cooking_times'] else 'None detected'}</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Main results in columns
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("🛒 Shopping List")
                st.markdown("*Clean, actionable shopping list:*")
                
                if shopping_list:
                    for i, item in enumerate(shopping_list, 1):
                        st.markdown(f"""
                        <div class="shopping-item">
                        <strong>{i}.</strong> {item}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Download button for shopping list
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
                st.subheader("🌡️ Cooking Parameters")
                
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
                
                # Processing stats
                st.markdown("**📊 Processing Stats:**")
                st.write(f"• Pages processed: {result['usage_info']['pages_processed']}")
                st.write(f"• Document size: {result['usage_info']['doc_size_bytes']:,} bytes")
            
            # Detailed ingredients and instructions
            with st.expander("📖 Detailed Ingredients & Instructions", expanded=False):
                col_ing, col_inst = st.columns([1, 1])
                
                with col_ing:
                    st.subheader(f"🥗 Ingredients ({len(recipe['ingredients'])})")
                    for ingredient in recipe['ingredients']:
                        st.write(f"• {ingredient}")
                
                with col_inst:
                    st.subheader(f"👨‍🍳 Cooking Steps ({len(recipe['instructions'])})")
                    for i, step in enumerate(recipe['instructions'], 1):
                        clean_step = step.replace('\n', ' ').strip()
                        st.write(f"{i}. {clean_step}")
            
            # Raw extracted content
            with st.expander("📄 Raw Extracted Content", expanded=False):
                st.markdown("*This is the raw markdown extracted by Document AI:*")
                st.code(full_content, language="markdown")
            
            # Save structured data
            output_data = {
                "recipe": recipe,
                "cooking_info": temps_times,
                "shopping_list": shopping_list,
                "original_pages": len(result['pages']),
                "document_size": result['usage_info']['doc_size_bytes']
            }
            
            # Download structured data
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
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

else:
    st.info("👆 Please upload a PDF file to begin the demo")
    
    # Sample/demo section when no file is uploaded
    st.markdown("---")
    st.subheader("🎯 How It Works")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **📄 Step 1: Upload**
        
        Upload any recipe PDF:
        - Cookbook pages
        - Recipe cards  
        - Blog screenshots
        - Handwritten recipes
        """)
    
    with col2:
        st.markdown("""
        **🧠 Step 2: AI Processing**
        
        Mistral Document AI:
        - Extracts text
        - Preserves formatting
        - Handles complex layouts
        - Recognizes structure
        """)
    
    with col3:
        st.markdown("""
        **🛒 Step 3: Smart Output**
        
        Get structured results:
        - Clean shopping list
        - Cooking parameters
        - Step-by-step instructions
        - Downloadable formats
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🤖 Powered by Mistral Document AI x Azure AI Foundry</p>
    <p>Transform any recipe PDF into actionable cooking data!</p>
</div>
""", unsafe_allow_html=True)
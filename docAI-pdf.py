import os
import base64
import requests
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def encode_pdf_to_base64(pdf_path):
    """Read a PDF file and encode it to base64"""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            base64_encoded = base64.b64encode(pdf_content).decode('utf-8')
            return base64_encoded
    except FileNotFoundError:
        print(f"❌ Error: PDF file not found at {pdf_path}")
        return None
    except Exception as e:
        print(f"❌ Error reading PDF file: {e}")
        return None

def process_pdf_with_mistral(pdf_path):
    """Process a local PDF file using Mistral Document AI"""
    
    print("🔄 DEMO: PDF to Structured Data with Mistral Document AI")
    print("=" * 60)
    
    # Get API key from environment
    api_key = os.getenv('AZURE_API_KEY')
    if not api_key:
        print("❌ Error: AZURE_API_KEY not found in environment variables")
        return None
    
    # Show file info
    file_size = os.path.getsize(pdf_path) / 1024  # KB
    print(f"📄 Input File: {pdf_path}")
    print(f"📊 File Size: {file_size:.1f} KB")
    
    # Encode PDF to base64
    print(f"\n🔄 Step 1: Encoding PDF to base64...")
    time.sleep(1)  # Demo pause
    base64_content = encode_pdf_to_base64(pdf_path)
    if not base64_content:
        return None
    
    print(f"✅ Encoded {len(base64_content):,} characters")
    
    # API endpoint and headers
    azure_endpoint = os.getenv('AZURE_ENDPOINT')
    url = azure_endpoint
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Request payload
    model_name = os.getenv('MODEL_NAME')
    payload = {
        "model": model_name,
        "document": {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{base64_content}"
        },
        "include_image_base64": True
    }
    
    try:
        print(f"\n🚀 Step 2: Sending to Mistral Document AI...")
        print(f"🔗 Endpoint: {url}")
        time.sleep(1)  # Demo pause
        
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload)
        end_time = time.time()
        
        response.raise_for_status()
        
        result = response.json()
        processing_time = end_time - start_time
        
        print(f"✅ Success! Processing completed in {processing_time:.2f} seconds")
        print(f"📄 Pages processed: {result['usage_info']['pages_processed']}")
        print(f"📊 Document size: {result['usage_info']['doc_size_bytes']:,} bytes")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making API request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return None

def main():
    print("🎯 DEMO SCENARIO: Recipe PDF to Shopping List")
    print("=" * 60)
    print("Problem: I have a recipe PDF and want to:")
    print("  • Extract the text accurately")
    print("  • Generate a shopping list")
    print("  • Get cooking parameters")
    print("\nSolution: AI-powered document processing!\n")
    
    # Example usage - replace with your actual PDF path
    pdf_path = "your_document.pdf"  # Put your PDF file in the same directory
    
    # Check if PDF file exists
    if not os.path.exists(pdf_path):
        print(f"📁 Please place your PDF file in the project directory.")
        print(f"📂 Current directory: {os.getcwd()}")
        print("\n🔍 Available PDF files:")
        pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
        if pdf_files:
            for file in pdf_files:
                print(f"  📄 {file}")
            pdf_path = pdf_files[0]
            print(f"\n🎯 Using: {pdf_path}")
        else:
            print("  ❌ No PDF files found")
            return
    
    # Process the PDF
    result = process_pdf_with_mistral(pdf_path)
    
    if result:
        # Save result
        output_file = "document_ai_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Raw extraction saved to: {output_file}")
        
        # Show preview
        print(f"\n👀 PREVIEW - First 200 characters:")
        print("-" * 40)
        first_page_content = result['pages'][0]['markdown'][:200]
        print(f"{first_page_content}...")
        
        print(f"\n🎉 DEMO COMPLETE - Ready for Phase 2!")
        print(f"▶️  Next: Run 'python parse-content-pdf.py' to see the magic!")

if __name__ == "__main__":
    main()
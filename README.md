# Mistral Document AI

![Mistral Document AI](../../Images/thumbnail-mistral-document-AI.png)

The future of document intelligence is here with Mistral Document AI in Azure AI Foundry. In this episode, April shows you how the model parses complex layouts from PDFs and handwritten notes. You’ll also see how the model’s structured JSON output makes it possible to integrate with databases, AI agents, and RAG workflows—turning unstructured documents into actionable data.

Try it yourself in Azure AI Foundry and start parsing documents and images: [ai.azure.com](https://ai.azure.com)

Learn more about Mistral Document AI: [aka.ms/insideAIF/mistral-document-AI](https://aka.ms/insideAIF/mistral-docuemnt-AI)

## Prerequisites

- An [Azure AI Foundry](https://ai.azure.com) project

## Run the Sample

### Document AI with base64 PDF

1. Navigate to the folder: `cd Samples/Mistral-Document-AI`
1. Install dependencies: `pip install -r requirements.txt`
1. Set up environment variables: `copy .env.example .env`
1. Put your PDF file in the same directory and replace `"your_document.pdf"` with the file name.
1. Run the script: `python docAI-pdf.py`
1. Confirm that the `docAI-pdf.py` run is successful and that a new `document_ai_result.json` file is created.
1. To parse the recipe content and extract structured components, run the script: `python parse-content-pdf.py`.

### Document AI with base64 PDF via a web-app

1. Navigate to the folder: `cd Samples/Mistral-Document-AI`
1. Install dependencies: `pip install -r requirements.txt`
1. Set up environment variables: `copy .env.example .env`
1. Run the command: `streamlit run app.py`
1. This will open a web interface where you can upload PDF files and process them with the Mistral Document AI service.

### Document AI with base64 image

1. Navigate to the folder: `cd Samples/Mistral-Document-AI`
1. Install dependencies: `pip install -r requirements.txt`
1. Set up environment variables: `copy .env.example .env`
1. Put your image file in the same directory and replace `"your_image.jpg"` with the file name.
1. Run the script: `python docAI-image.py`
1. Confirm that the `docAI-image.py` run is successful and that a new `document_ai_result.json` file is created.
1. To parse the recipe content and extract structured components, run the script: `python parse-content-image.py`.
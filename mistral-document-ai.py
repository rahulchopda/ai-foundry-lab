import os
import base64
import requests
import json
import time
from dotenv import load_dotenv

# Example: Set up credentials/environment variables for Azure AI Foundry
AZURE_AIFOUNDRY_ENDPOINT = os.getenv("AZURE_AIFOUNDRY_ENDPOINT", "https://your-foundry-endpoint")
AZURE_AIFOUNDRY_KEY = os.getenv("AZURE_AIFOUNDRY_KEY", "your-api-key")
MISTRAL_MODEL_ID = os.getenv("MISTRAL_MODEL_ID", "mistral-document-ai")

def call_mistral_document_ai_via_foundry(document_path, additional_params=None):
    """
    Calls the Mistral Document AI model via Azure AI Foundry.
    :param document_path: Path to the PDF/document file
    :param additional_params: Dict of other params, such as OCR hints or extraction options
    :return: Foundry API JSON response
    """
    url = f"{AZURE_AIFOUNDRY_ENDPOINT}/models/{MISTRAL_MODEL_ID}/invoke"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_AIFOUNDRY_KEY
    }
    files = {
        "file": open(document_path, "rb")
    }
    data = additional_params or {}

    response = requests.post(url, headers=headers, files=files, data=data)
    response.raise_for_status()
    return response.json()

# Example Job Launcher for batch/asynchronous execution
def launch_mistral_job(document_path, job_metadata=None):
    """
    Launches an asynchronous Mistral Document AI job via Foundry.
    :param document_path: Path to document file
    :param job_metadata: Dict, optional metadata
    :return: Job submission response (job_id, status, etc.)
    """
    url = f"{AZURE_AIFOUNDRY_ENDPOINT}/jobs"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_AIFOUNDRY_KEY
    }
    files = {
        "file": open(document_path, "rb")
    }
    data = {
        "model_id": MISTRAL_MODEL_ID,
        "metadata": json.dumps(job_metadata or {})
    }

    response = requests.post(url, headers=headers, files=files, data=data)
    response.raise_for_status()
    return response.json()

def get_job_status(job_id):
    """
    Polls the job status from Azure AI Foundry.
    """
    url = f"{AZURE_AIFOUNDRY_ENDPOINT}/jobs/{job_id}"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_AIFOUNDRY_KEY
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
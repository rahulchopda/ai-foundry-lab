import yaml
from openai import AzureOpenAI, OpenAI
from azure.identity import DefaultAzureCredential
from abc import ABC, abstractmethod
import re
from urllib.parse import urlparse
import os
import base64
import json
from typing import Dict, Any
import requests

credential = DefaultAzureCredential()

cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))
try:
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f) or {}
except FileNotFoundError:
    cfg = {}

# ...existing code...

# ---- Model handler classes + orchestrator ----
class BaseModelHandler(ABC):
    def __init__(self):
        self.model_name = ""
        self.endpoint = ""
        self.api_key = ""

    @abstractmethod
    def call(self, prompt: str) -> dict:
        raise NotImplementedError

    # ...existing code...
    @staticmethod
    def format_completion_output(completion) -> dict:
        """
        Robust extraction of common fields from different SDK/dict shapes.
        Returns standardized dict: { content, metrics: {token_usage, cost_estimate}, guardrails, monitoring, raw }
        """
        def _get(obj, key, default=None):
            try:
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)
            except Exception:
                return default

        # --- content extraction ---
        content = None
        choices = _get(completion, "choices")
        first_choice = None
        if isinstance(choices, (list, tuple)) and len(choices) > 0:
            first_choice = choices[0]

        if first_choice:
            # try common dict shape: {"message": {"content": "..."}} or {"text": "..."}
            if isinstance(first_choice, dict):
                msg = first_choice.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content") or (msg.get("content", {}).get("text") if isinstance(msg.get("content"), dict) else None)
                content = content or first_choice.get("text")
            else:
                # SDK object shapes
                msg = _get(first_choice, "message")
                if msg is not None:
                    content = _get(msg, "content") or getattr(msg, "content", None)
                content = content or _get(first_choice, "text")

        # fallback top-level fields
        content = content or _get(completion, "content") or _get(completion, "output") or _get(completion, "output_text")

        # --- token usage extraction ---
        token_usage = None
        usage = _get(completion, "usage")
        if usage:
            token_usage = _get(usage, "total_tokens") or getattr(usage, "total_tokens", None)
        if token_usage is None:
            # other possible locations
            token_usage = _get(completion, "token_count") or _get(completion, "total_tokens")

        # --- request id / monitoring ---
        request_id = _get(completion, "id") or _get(completion, "request_id") or getattr(completion, "id", None)

        # --- guardrails / content filter info ---
        guardrails = {
            "filtered": False,
            "top_level": None,
            "choices": [],
            "prompt_filter_results": None,
            "custom_blocklists": {"filtered": False, "details": []}
        }

        return {
            "content": content,
            "metrics": {
                "token_usage": token_usage
            },
            "guardrails": guardrails,
            "monitoring": {
                "request_id": request_id
            },
            "raw": completion
        }

class OpenAIHandlerMixin:
    def make_openai_client(self, endpoint: str):
        return OpenAI(
            base_url=endpoint,
            api_key=self.api_key
        )

class GPT4OHandler(BaseModelHandler, OpenAIHandlerMixin):
    def __init__(self):
        self.model_name = "gpt-4o"
        self.endpoint = cfg.get("MODEL_ENDPOINTS")[self.model_name].strip()
        self.api_key = cfg.get("API_KEY")

    def call(self, prompt: str) -> dict:
        client = self.make_openai_client(self.endpoint)
        messages = [
            {"role": "system", "content": "You are a AI assistant."},
            {"role": "user", "content": prompt},
        ]
        completion = client.chat.completions.create(model=self.model_name, messages=messages)
        return self.format_completion_output(completion)

class GPT41Handler(BaseModelHandler, OpenAIHandlerMixin):
    def __init__(self):
        self.model_name = "gpt-4.1"
        self.endpoint = cfg.get("MODEL_ENDPOINTS")[self.model_name].strip()
        self.api_key = cfg.get("API_KEY")

    def call(self, prompt: str) -> dict:
        client = self.make_openai_client(self.endpoint)
        messages = [
            {"role": "system", "content": "You are a AI assistant."},
            {"role": "user", "content": prompt},
        ]
        completion = client.chat.completions.create(model=self.model_name, messages=messages)
        return self.format_completion_output(completion)

def encode_file_to_base64(file_path: str) -> str:
    """Encode a file to base64 string."""
    try:
        print(file_path)
        with open(file_path, "rb") as file:
            return base64.b64encode(file.read()).decode('utf-8')
    except Exception as e:
        raise Exception(f"Error encoding file to base64: {str(e)}")

class MistralDocumentAIHandler(BaseModelHandler):
    def __init__(self):
        self.model_name = "mistral-document-ai"
        self.endpoint = cfg.get("MODEL_ENDPOINTS")[self.model_name].strip()
        self.api_key = cfg.get("API_KEY")

    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to Mistral Document AI endpoint with base64-encoded payload and response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Encode the entire payload to base64
        payload_json = json.dumps(payload)
        base64_payload = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')

        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json={"data": base64_payload},
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()

            # Decode base64 response if present
            if "data" in response_data and isinstance(response_data["data"], str):
                try:
                    decoded_data = base64.b64decode(response_data["data"]).decode('utf-8')
                    response_data = json.loads(decoded_data)
                except Exception as e:
                    response_data["error"] = f"Failed to decode base64 response: {str(e)}"
            return response_data
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")

    def call(self, document_path: str, instructions: str = None) -> dict:
        """
        Process a document using Mistral Document AI with base64-encoded input.
        Args:
            document_path: Path to the document file (PDF, image, etc.)
            instructions: Optional instructions for document processing
        """
        # Convert input document to base64
        try:
            print(document_path)
            base64_content = encode_file_to_base64(document_path)
        except Exception as e:
            return {
                "content": None,
                "metrics": {"error": str(e)},
                "guardrails": {},
                "monitoring": {},
                "raw": {"error": str(e)}
            }

        # Prepare payload with base64-encoded document
        payload = {
            "document": {
                "content": base64_content,
                "mime_type": self._detect_mime_type(document_path)
            },
            "instructions": instructions or "Extract and summarize the key information from this document."
        }

        # Make API request
        try:
            response = self._make_request(payload)
        except Exception as e:
            return {
                "content": None,
                "metrics": {"error": str(e)},
                "guardrails": {},
                "monitoring": {},
                "raw": {"error": str(e)}
            }

        # Format the response
        formatted_response = self._format_mistral_response(response)
        return formatted_response

    def _detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type based on file extension."""
        _, ext = os.path.splitext(file_path.lower())
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain'
        }
        return mime_types.get(ext, 'application/octet-stream')

    def _format_mistral_response(self, response: Dict[str, Any]) -> dict:
        """Format Mistral Document AI response to match the standard output format."""
        content = None
        error = None

        if "error" in response:
            error = response["error"]
            content = f"Error processing document: {error}"
        else:
            content = response.get("text") or response.get("content") or response.get("output")
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
            if not content:
                extracted_content = response.get("extracted_content", {})
                if extracted_content:
                    content = "\n".join([
                        f"{key}: {value}" for key, value in extracted_content.items()
                        if isinstance(value, str) and value.strip()
                    ])
                else:
                    content = "Document processed successfully but no text content extracted."

        return {
            "content": content,
            "metrics": {
                "token_usage": None,  # Document AI typically doesn't provide token counts
                "processing_time": response.get("processing_time"),
                "pages": response.get("page_count")
            },
            "guardrails": {
                "filtered": False,
                "document_valid": True
            },
            "monitoring": {
                "request_id": response.get("request_id") or response.get("id"),
                "status": response.get("status", "completed")
            },
            "raw": response
        }
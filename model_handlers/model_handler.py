import yaml
from openai import AzureOpenAI, OpenAI
from azure.identity import DefaultAzureCredential
from abc import ABC, abstractmethod
import re
from urllib.parse import urlparse
import os
credential = DefaultAzureCredential()
import os

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
        self.api_key =  ""


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
        self.api_key =  cfg.get("API_KEY")

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
        self.api_key =  cfg.get("API_KEY")

    def call(self, prompt: str) -> dict:
        client = self.make_openai_client(self.endpoint)
        messages = [
            {"role": "system", "content": "You are a AI assistant."},
            {"role": "user", "content": prompt},
        ]
        completion = client.chat.completions.create(model=self.model_name, messages=messages)
        return self.format_completion_output(completion)
import yaml
from openai import AzureOpenAI, OpenAI
from azure.identity import DefaultAzureCredential
from abc import ABC, abstractmethod
import re
from urllib.parse import urlparse
import os
credential = DefaultAzureCredential()
import ast
import re
import ast
from typing import Tuple, Dict, Any
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage

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

    @staticmethod
    def count_filtered_false(self, obj: Any) -> int:    
        count = 0
        if isinstance(obj, dict):
            if 'filtered' in obj:
                try:
                    if obj['filtered'] is False:
                        return 1
                except Exception:
                    pass
            for v in obj.values():
                count += self.count_filtered_false(v)
        elif isinstance(obj, list):
            for item in obj:
                count += self.count_filtered_false(item)
        return count

    @staticmethod
    def format_completion_output(self, raw) -> dict:
        """
        Robust extraction of common fields from different SDK/dict shapes.
        Returns standardized dict: { content, metrics: {token_usage, cost_estimate}, guardrails, monitoring, raw }
        """
        model_response = ""
        total_tokens = -1
        safety_details = {}
        print("raw:", raw)
        try:
            # 1) Extract model response text (choices[0].message.content)
            m = re.search(
                r"message=ChatCompletionMessage\(\s*content=(?:r?|'|\")(?P<content>.*?)(?:'|\")\s*,\s*refusal",
                raw,
                re.DOTALL,
            )
            if m:
                # unescape common escapes
                model_response = m.group("content").encode("utf-8").decode("unicode_escape")
                model_response = model_response.strip()

            # 2) Extract total_tokens (usage.total_tokens=XXX)
            t = re.search(r"total_tokens\s*=\s*(\d+)", raw)
            if t:
                total_tokens = int(t.group(1))

            # 3) Extract content_filter_results dict from the first choice (choices[...] content_filter_results={...})
            # We search for the first occurrence of "content_filter_results=" followed by a balanced {...}
            cf_match = re.search(r"content_filter_results\s*=\s*(\{)", raw)
            if cf_match:
                # find balanced braces starting at cf_match.start(1)
                start = cf_match.start(1)
                depth = 0
                i = start
                while i < len(raw):
                    ch = raw[i]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                    i += 1
                else:
                    end = None

                if end:
                    cf_text = raw[start:end]
                    # Replace Python's 'False'/'True' with Python literal (ast can handle them),
                    # and ensure we have valid Python dict literal. ast.literal_eval can parse it.
                    try:
                        safety_details = ast.literal_eval(cf_text)
                    except Exception:
                        # fallback: try replacing common 'false'/'true' variants and single quotes
                        cf_text_fixed = cf_text.replace("false", "False").replace("true", "True")
                        try:
                            safety_details = ast.literal_eval(cf_text_fixed)
                        except Exception:
                            safety_details = {}

            # 4) Count flags where filtered == False
            num_safe_flags = self.count_filtered_false(safety_details)

        except Exception:
            # On parse failure return what we have
            num_safe_flags = self.count_filtered_false(safety_details)
        
        print("model_response:", model_response)
        print("total_tokens:", total_tokens)
        print("num_safe_flags:", num_safe_flags)
        print("safety_details:", safety_details)

        return model_response, total_tokens, num_safe_flags, safety_details

            
        

class OpenAIHandlerMixin:
    def make_openai_client(self, endpoint: str):
        return OpenAI(
            base_url=endpoint,
            api_key=self.api_key
        )
    
class GPT41MiniHandler(BaseModelHandler, OpenAIHandlerMixin):
    def __init__(self):
        self.model_name = "gpt-4.1-mini"
        self.endpoint = cfg.get("MODEL_ENDPOINTS")[self.model_name].strip()
        self.api_key =  cfg.get("API_KEY")

    def call(self, prompt: str) -> dict:
        client = self.make_openai_client(self.endpoint)
        messages = [
            {"role": "system", "content": "You are a AI assistant."},
            {"role": "user", "content": prompt},
        ]
        try:
            completion = client.chat.completions.create(model=self.model_name, messages=messages)
            return completion
        except Exception as e:
                raise Exception(f"Failed to parse response: {str(e)}")  

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
        try:
            completion = client.chat.completions.create(model=self.model_name, messages=messages)
            print("raw:", completion)
            return completion
            #return self.format_completion_output(completion)
        except Exception as e:
            raise Exception(f"Failed to parse response: {str(e)}")  
        
class PhiHandler(BaseModelHandler, OpenAIHandlerMixin):
    def __init__(self):
        self.model_name = "Phi-4-mini-instruct"
        self.endpoint = cfg.get("MODEL_ENDPOINTS")[self.model_name].strip()
        self.api_key =  cfg.get("API_KEY")

    def call(self, prompt: str) -> dict:
        client = self.make_openai_client(self.endpoint)
        messages = [
            {"role": "system", "content": "You are a AI assistant."},
            {"role": "user", "content": prompt},
        ]
        try:
            print(self.model_name)
            completion = client.chat.completions.create(model=self.model_name, messages=messages)
            print("raw:", completion)
            return completion
            #return self.format_completion_output(completion)
        except Exception as e:
            raise Exception(f"Failed to parse response: {str(e)}")  
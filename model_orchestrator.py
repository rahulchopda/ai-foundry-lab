import os
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from typing import Optional, Dict

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import fitz
#from guardrails import apply_guradrails
from governance_logger import log_interaction, load_logs
import yaml
from model_handlers.model_handler import BaseModelHandler, GPT4OHandler, GPT41Handler



class ModelOrchestrator:
    HANDLER_MAP = {
        "gpt-4o": GPT4OHandler,
        "gpt-4.1": GPT41Handler
    }

    def __init__(self, endpoints: dict, api_key: str):
        self.endpoints = endpoints or {}
        self.api_key = api_key


    def get_handler(self, model_name: str) -> BaseModelHandler:
        handler_cls = self.HANDLER_MAP.get(model_name)
        if not handler_cls:
            raise ValueError(f"Unsupported model: {model_name}")
        return handler_cls()

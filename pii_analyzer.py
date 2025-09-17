import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from dataclasses import dataclass

@dataclass
class PIIEntity:
    text: str
    category: str
    confidence_score: float
    offset: int
    length: int

class PIIHandler:
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        """
        Initialize TextAnalytics with API key and endpoint.
        If not provided, will attempt to load from environment variables.
        """
        # Load environment variables from .env file if present
        load_dotenv()
        
        # Use provided credentials or load from environment
        self.api_key = api_key or os.getenv('AZURE_TEXT_ANALYTICS_KEY')
        self.endpoint = endpoint or os.getenv('AZURE_TEXT_ANALYTICS_ENDPOINT')
        
        if not self.api_key or not self.endpoint:
            raise ValueError("API key and endpoint must be provided either directly or through environment variables")

        self.client = self._authenticate_client(self.api_key, self.endpoint)
    
    def _authenticate_client(self, api_key: str, endpoint: str) -> TextAnalyticsClient:
        """Create and authenticate the Text Analytics client"""
        credential = AzureKeyCredential(api_key)
        return TextAnalyticsClient(endpoint=endpoint, credential=credential)

    def analyze_text(self, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Analyze PII entities in a single text string.
        
        Args:
            text: String to analyze
            language: Language code (default: "en")
            
        Returns:
            Dictionary containing PII analysis results
        """
        try:
            response = self.client.recognize_pii_entities([text], language=language)
            doc = response[0]

            if doc.is_error:
                return {
                    "success": False,
                    "error": f"Error: {doc.error}",
                    "original_text": text,
                    "redacted_text": text
                }

            return {
                "success": True,
                "original_text": text,
                "redacted_text": doc.redacted_text,
                "entities": [
                    PIIEntity(
                        text=entity.text,
                        category=entity.category,
                        confidence_score=entity.confidence_score,
                        offset=entity.offset,
                        length=entity.length
                    ) for entity in doc.entities
                ]
            }

        except Exception as e:
            raise Exception(f"Error analyzing PII entities: {str(e)}")
import requests
import json
from app.providers.base import VisionProvider
from app.utils.logger import get_logger

logger = get_logger("GeminiProvider")

class GeminiProvider(VisionProvider):
    """Gemini Multimodal API Provider using REST API for maximum packaging compatibility."""
    
    def __init__(self):
        self.api_key = ""
        # Default to 2.5-flash as it is the standard model in 2026.
        self.model_name = "gemini-2.5-flash"
        
    def initialize(self, api_key: str) -> bool:
        if not api_key:
            logger.error("Empty API key provided to Gemini Provider.")
            return False
        self.api_key = api_key
        return self.test_connection()

    def test_connection(self) -> bool:
        """Verify API key validity by making a lightweight request."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": "Hello"}]
            }]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info("Gemini API connection test successful.")
                return True
            else:
                logger.error(f"Gemini API connection test failed. Code: {response.status_code}, Error: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Connection test failed with exception: {e}")
            return False

    def classify_document(self, base64_images: list) -> str:
        """Classify if the document is a COA, SDS, Invoice, or Unknown."""
        if not self.api_key:
            raise ValueError("Gemini API Key is not initialized.")
            
        if not base64_images:
            return "Unknown"
            
        # Use first page only for quick and cost-effective classification
        first_page = base64_images[0]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        prompt = (
            "Determine the document type of this page. "
            "Choose only from: 'COA' (Certificate of Analysis), 'SDS' (Safety Data Sheet), "
            "'Invoice', or 'Unknown'. Return the result strictly in JSON."
        )
        
        # JSON Schema for classification
        schema = {
            "type": "OBJECT",
            "properties": {
                "doctype": { "type": "STRING", "enum": ["COA", "SDS", "Invoice", "Unknown"] }
            },
            "required": ["doctype"]
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": first_page
                        }
                    }
                ]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                res_data = response.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text.strip())
                return result.get("doctype", "Unknown")
            else:
                logger.error(f"Classification request failed: {response.status_code} - {response.text}")
                return "Unknown"
        except Exception as e:
            logger.error(f"Failed to classify document: {e}")
            return "Unknown"

    def extract_coa_fields(self, base64_images: list, schema: dict) -> dict:
        """Extract COA fields using Gemini Multimodal structured JSON output."""
        if not self.api_key:
            raise ValueError("Gemini API Key is not initialized.")
            
        if not base64_images:
            raise ValueError("No images provided for extraction.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        # Construct content parts. First, add the text prompt, then all page images.
        prompt = (
            "You are a professional chemical/food certificate of analysis (COA) data extraction expert. "
            "Examine all provided pages of the COA document. Extract the raw text values for the requested fields. "
            "If a field cannot be found on the pages, fill it as 'N/A'. "
            "For each field, rate your extraction confidence level as 'high', 'medium', or 'low'. "
            "Under 'traceability', provide the page number and original sentence/context where the field was found."
        )
        
        parts = [{"text": prompt}]
        for b64_img in base64_images:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": b64_img
                }
            })
            
        payload = {
            "contents": [{
                "parts": parts
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema
            }
        }
        
        try:
            # Multi-page multimodal requests might take a bit longer
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                extracted_json = json.loads(text.strip())
                return extracted_json
            else:
                logger.error(f"Field extraction failed: {response.status_code} - {response.text}")
                raise Exception(f"API Error Code {response.status_code}")
        except Exception as e:
            logger.error(f"Gemini extraction exception: {e}")
            raise e

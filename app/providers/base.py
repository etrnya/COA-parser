from abc import ABC, abstractmethod

class VisionProvider(ABC):
    """Abstract Base Class defining the interface for all Vision Extraction engines."""
    
    @abstractmethod
    def initialize(self, api_key: str) -> bool:
        """Initialize the client with the provided API key. Return True if successful."""
        pass

    @abstractmethod
    def classify_document(self, base64_images: list) -> str:
        """
        Classify the document type.
        
        Args:
            base64_images: List of base64-encoded optimized image strings (pages).
            
        Returns:
            str: Document class name, e.g. "COA", "SDS", "Invoice", "Unknown".
        """
        pass

    @abstractmethod
    def extract_coa_fields(self, base64_images: list, schema: dict) -> dict:
        """
        Extract structured fields from COA document pages based on the provided schema.
        
        Args:
            base64_images: List of base64-encoded optimized image strings.
            schema: The target schema (JSON Schema dict) mapping fields to capture.
            
        Returns:
            dict: Structured JSON response containing the extracted values and confidence metrics.
        """
        pass

from app.providers.base import VisionProvider
from app.utils.logger import get_logger

logger = get_logger("Classifier")

def classify_coa_document(provider: VisionProvider, base64_images: list) -> str:
    """
    Classify the document type to make sure it is a COA.
    
    Args:
        provider: Initialized VisionProvider instance.
        base64_images: List of base64 JPEG pages.
        
    Returns:
        str: "COA", "SDS", "Invoice", or "Unknown".
    """
    if not base64_images:
        return "Unknown"
        
    try:
        logger.info("Running document classification...")
        doc_type = provider.classify_document(base64_images)
        logger.info(f"Classification result: {doc_type}")
        return doc_type
    except Exception as e:
        logger.error(f"Error during document classification: {e}")
        return "Unknown"

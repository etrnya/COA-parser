import os
import io
import hashlib
import gc
import base64
from PIL import Image
import fitz  # PyMuPDF
from app.utils.logger import get_logger

logger = get_logger("Preprocessor")

def calculate_sha256(file_path: str) -> str:
    """Calculate the SHA-256 hash of a file's binary content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks of 64KB
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def preprocess_image(image_bytes: bytes, max_dim: int = 1200, quality: int = 80) -> str:
    """
    Resize, grayscale, and JPEG compress a raw image to optimize payload size.
    
    Args:
        image_bytes: Raw binary bytes of the image.
        max_dim: Maximum size (width or height) allowed.
        quality: JPEG compression quality (0-100).
        
    Returns:
        str: Base64-encoded string of the optimized JPEG.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # 1. Convert to Grayscale to save bandwidth and API tokens
        if img.mode != 'L':
            img = img.convert('L')
            
        # 2. Downscale if dimensions exceed limits
        w, h = img.size
        if w > max_dim or h > max_dim:
            if w > h:
                new_w = max_dim
                new_h = int(h * (max_dim / w))
            else:
                new_h = max_dim
                new_w = int(w * (max_dim / h))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
        # 3. Compress as JPEG into memory buffer
        out_buf = io.BytesIO()
        img.save(out_buf, format="JPEG", quality=quality)
        optimized_bytes = out_buf.getvalue()
        
        # Cleanup
        img.close()
        out_buf.close()
        
        # Base64 encode
        return base64.b64encode(optimized_bytes).decode("utf-8")
        
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        raise e

def preprocess_pdf(file_path: str, max_dim: int = 1200, quality: int = 80) -> list:
    """
    Convert a multi-page PDF into a list of optimized, base64-encoded JPEG strings.
    Ensures Fitz documents and pixmaps are explicitly deleted to prevent memory leaks.
    
    Args:
        file_path: Path to the local PDF file.
        max_dim: Maximum size of image edges.
        quality: Compression quality.
        
    Returns:
        list: List of base64-encoded page images.
    """
    logger.info(f"Converting PDF to optimized images: {os.path.basename(file_path)}...")
    base64_pages = []
    doc = None
    
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Render page to Pixmap (150 DPI is standard for document readability)
            pix = page.get_pixmap(dpi=150)
            
            # Get PNG bytes from Pixmap
            png_bytes = pix.tobytes("png")
            
            # Preprocess using the image pipeline
            b64_img = preprocess_image(png_bytes, max_dim=max_dim, quality=quality)
            base64_pages.append(b64_img)
            
            # Explicitly delete Pixmap to free C memory bindings in PyMuPDF
            del pix
            
        logger.info(f"Rendered {len(base64_pages)} pages from PDF.")
        
    except Exception as e:
        logger.error(f"PDF processing failed for {file_path}: {e}")
        raise e
    finally:
        if doc:
            doc.close()
            del doc
        # Run Garbage Collector immediately to free up rendered pages
        gc.collect()
        
    return base64_pages

def preprocess_file(file_path: str) -> list:
    """
    Unified entry point to convert any supported file type (PDF/JPG/PNG)
    into a list of base64-encoded optimized image strings.
    """
    ext = os.path.splitext(file_path.lower())[1]
    
    if ext == ".pdf":
        return preprocess_pdf(file_path)
    elif ext in [".jpg", ".jpeg", ".png"]:
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            optimized_b64 = preprocess_image(img_bytes)
            return [optimized_b64]
        except Exception as e:
            logger.error(f"Failed to read image file {file_path}: {e}")
            raise e
    else:
        raise ValueError(f"Unsupported file format: {ext}")

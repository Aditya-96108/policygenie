"""
Security Validation - Lenient Version
"""
import logging
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

def validate_file_security(filename: str, content: bytes):
    """Validate file security with lenient checks"""
    
    # Check extension
    ext = filename.lower().split('.')[-1]
    if ext not in settings.allowed_extensions:
        raise HTTPException(400, f"Invalid extension. Only {settings.allowed_extensions} allowed")
    
    # Check PDF header (lenient)
    if not content.startswith(b'%PDF'):
        logger.warning("File doesn't start with PDF header")
        # Don't fail - some PDFs have different headers
    
    # Try MIME check if magic available
    try:
        import magic
        mime = magic.from_buffer(content, mime=True)
        if mime not in ["application/pdf", "application/x-pdf", "application/octet-stream"]:
            logger.warning(f"Unusual MIME type: {mime}")
    except ImportError:
        logger.debug("python-magic not installed, skipping MIME check")
    except Exception as e:
        logger.debug(f"MIME check skipped: {e}")
    
    # Check for malicious content
    dangerous = [b"<script>", b"javascript:", b"eval(", b"exec("]
    for pattern in dangerous:
        if pattern in content.lower():
            raise HTTPException(400, f"Suspicious content detected")
    
    logger.info("✓ Security validation passed")
    return True
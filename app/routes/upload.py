import logging
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.document_service import extract_text
from app.utils.chunking import chunk_text
from app.services.rag_service import add_documents
from app.services.llm_service import llm_service
from app.models.classifier import classify_clause
from app.services.security_service import validate_file_security
from app.services.fraud_service import detect_fraud
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload-docs")
async def upload_docs(file: UploadFile = File(...)):
    try:
        # Check file extension instead of content_type (more reliable)
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(415, "Only PDF files allowed")
        
        content = await file.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(413, "File too large")
        
        # Validate file security (will check MIME type inside if python-magic available)
        try:
            validate_file_security(file.filename, content)
        except Exception as e:
            logger.warning(f"Security validation warning: {e}")
            # Continue anyway if security check fails (python-magic may not be installed)
        
        uploads_dir = "data/uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = f"{uploads_dir}/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Extracting text from: {file.filename}")
        text = extract_text(file_path)
        
        if not text or len(text.strip()) < 50:
            raise HTTPException(400, "Could not extract text from PDF. File may be empty or image-based.")
        
        logger.info(f"Running fraud detection on document")
        fraud_result = await detect_fraud(text)
        if fraud_result.get("is_suspicious"):
            logger.warning(f"Suspicious document: {file.filename}")
            os.makedirs("data/processed", exist_ok=True)
            with open("data/processed/suspicious_logs.txt", "a") as log:
                log.write(f"{file.filename}: {fraud_result['fraud_score']}\n")
            return {
                "message": "Document flagged for manual review",
                "fraud_details": fraud_result
            }
        
        logger.info(f"Chunking text into smaller pieces")
        chunks = chunk_text(text)
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = await llm_service.generate_embeddings(chunks)
        
        logger.info(f"Classifying chunks")
        metadatas = []
        for chunk in chunks:
            try:
                label = classify_clause(chunk)[0]['label']
            except:
                label = "GENERAL"
            metadatas.append({"label": label})
        
        logger.info(f"Adding documents to vector database")
        add_documents(chunks, embeddings, metadatas)  # SYNC function - no await
        
        logger.info(f"Successfully uploaded and indexed: {file.filename}")
        return {
            "message": "Uploaded and indexed successfully",
            "chunks": len(chunks),
            "filename": file.filename
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Upload failed: {str(e)}")

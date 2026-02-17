"""Enhanced RAG Service with Hybrid Search - Fixed for Production"""
import logging
from typing import List, Optional, Dict
import numpy as np
from app.db.chroma_client import collection

logger = logging.getLogger(__name__)


def add_documents(
    chunks: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[Dict]] = None
) -> None:
    """
    Add documents to ChromaDB vector database
    
    NOTE: Synchronous function - FAISS disabled for small datasets
    """
    try:
        # Generate unique IDs
        ids = [f"id_{i}_{hash(chunk)}" for i, chunk in enumerate(chunks)]
        
        # Add to ChromaDB
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas or [{}] * len(chunks)
        )
        
        logger.info(f"✓ Added {len(chunks)} documents to vector database")
        
    except Exception as e:
        logger.error(f"Add documents error: {str(e)}")
        raise


def retrieve(
    query_embedding: List[float],
    k: int = 5
) -> List[List[str]]:
    """
    Retrieve documents using ChromaDB semantic search
    """
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
        
        docs = results.get('documents', [])
        logger.info(f"Retrieved {len(docs[0]) if docs else 0} documents")
        return docs
        
    except Exception as e:
        logger.error(f"Retrieve error: {str(e)}")
        return []

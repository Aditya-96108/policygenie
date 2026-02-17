#!/bin/bash

# Create all __init__.py files
touch app/__init__.py app/core/__init__.py app/db/__init__.py app/models/__init__.py
touch app/routes/__init__.py app/schemas/__init__.py app/services/__init__.py app/utils/__init__.py

# Create DB clients
cat > app/db/chroma_client.py << 'EOF'
import chromadb
from chromadb.config import Settings
from app.config import settings

client = chromadb.Client(Settings(
    persist_directory=settings.chroma_path,
    anonymized_telemetry=False
))

collection = client.get_or_create_collection(
    name="policies",
    metadata={"hnsw:space": "cosine"}
)
EOF

cat > app/db/faiss_client.py << 'EOF'
import logging
import os
import pickle
import numpy as np
import faiss
from typing import List
from app.config import settings

logger = logging.getLogger(__name__)

class FAISSIndex:
    def __init__(self):
        self.index = None
        self.id_map = {}
        self.dimension = 3072
        self.index_path = settings.faiss_index_path
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            if os.path.exists(f"{self.index_path}.index"):
                self.index = faiss.read_index(f"{self.index_path}.index")
                with open(f"{self.index_path}.map", 'rb') as f:
                    self.id_map = pickle.load(f)
            else:
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
                self.index.nprobe = 10
        except:
            self.index = faiss.IndexFlatL2(self.dimension)
    
    async def add_vectors(self, vectors: np.ndarray, ids: List[str]):
        try:
            if not self.index.is_trained:
                self.index.train(vectors)
            start_idx = self.index.ntotal
            self.index.add(vectors.astype('float32'))
            for i, doc_id in enumerate(ids):
                self.id_map[start_idx + i] = doc_id
            self._save_index()
        except Exception as e:
            logger.error(f"Add vectors error: {e}")
    
    async def search(self, query_vectors: np.ndarray, k: int = 5):
        try:
            if self.index.ntotal == 0:
                return []
            distances, indices = self.index.search(query_vectors.astype('float32'), k)
            results = []
            for idx_list in indices:
                doc_ids = [self.id_map.get(idx, "") for idx in idx_list if idx in self.id_map]
                results.append(doc_ids)
            return results
        except:
            return []
    
    def _save_index(self):
        try:
            faiss.write_index(self.index, f"{self.index_path}.index")
            with open(f"{self.index_path}.map", 'wb') as f:
                pickle.dump(self.id_map, f)
        except Exception as e:
            logger.error(f"Save error: {e}")

faiss_index = FAISSIndex()
EOF

# Create Utils
cat > app/utils/chunking.py << 'EOF'
from typing import List
import tiktoken

def chunk_text(text: str, max_tokens: int = 500) -> List[str]:
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunks.append(encoding.decode(chunk_tokens))
    return chunks
EOF

cat > app/utils/prompts.py << 'EOF'
def get_claim_prompt(context: str, query: str) -> str:
    return f"""You are an expert insurance claims processor with multi-agent capabilities.

CONTEXT FROM POLICY DOCUMENTS:
{context}

CLAIM QUERY:
{query}

ANALYSIS FRAMEWORK:
1. Fraud Detection Agent: Analyze for red flags, inconsistencies, suspicious patterns
2. Coverage Verification Agent: Check policy coverage, exclusions, limits
3. Claims Approval Agent: Make decision based on evidence

OUTPUT (JSON):
{{
  "decision": "APPROVED/REJECTED/REQUIRES_REVIEW",
  "reason": "Detailed explanation with clause references",
  "coverage_amount": amount,
  "fraud_score": 0.0-1.0,
  "next_steps": ["action items"],
  "policy_references": ["clause numbers"]
}}"""

def get_risk_prompt(context: str, query: str) -> str:
    return f"""You are an expert insurance underwriter using advanced risk assessment.

POLICY CONTEXT:
{context}

APPLICANT QUERY:
{query}

ASSESSMENT FRAMEWORK:
1. Risk Scoring Agent: Analyze demographics, health, behavior, financial factors
2. Pricing Agent: Calculate personalized premium using dynamic pricing
3. Compliance Agent: Verify regulatory compliance

OUTPUT (JSON):
{{
  "risk_score": 0-100,
  "decision": "APPROVE/DECLINE/REVIEW",
  "premium_estimate": {{"annual": amount, "monthly": amount}},
  "risk_factors": ["specific factors identified"],
  "recommendations": ["personalized suggestions"],
  "compliance_status": "compliant/issues"
}}"""

def get_chat_prompt(context: str, query: str) -> str:
    return f"""You are a helpful insurance advisor.

POLICY CONTEXT:
{context}

CUSTOMER QUESTION:
{query}

Provide a clear, accurate answer with policy clause references where applicable."""

def get_fraud_prompt(text: str) -> str:
    return f"""You are a fraud detection specialist. Analyze the following for fraud indicators:

TEXT TO ANALYZE:
{text}

FRAUD INDICATORS TO CHECK:
- Urgency language ("urgent", "immediately", "asap")
- Multiple claims or incidents
- Inconsistent details or timeline
- Vague or missing evidence
- Unusual claim amounts
- Pre-existing condition concealment

OUTPUT FORMAT:
score: 0.XX (where 0.0 = no fraud indicators, 1.0 = highly suspicious)"""
EOF

# Create Document Service
cat > app/services/document_service.py << 'EOF'
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def extract_text(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Extract text error: {e}")
        raise
EOF

# Create Security Service
cat > app/services/security_service.py << 'EOF'
import logging
import magic
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

def validate_file_security(filename: str, content: bytes):
    ext = filename.lower().split('.')[-1]
    if ext not in settings.allowed_extensions:
        raise HTTPException(400, "Invalid file extension")
    
    try:
        mime = magic.from_buffer(content, mime=True)
        if mime != "application/pdf":
            raise HTTPException(400, "Invalid MIME type")
    except:
        pass  # magic not available, skip MIME check
    
    if b"<script>" in content or b"javascript:" in content.lower():
        raise HTTPException(400, "Suspicious content detected")
    
    logger.info("File security validated")
EOF

# Create Models
cat > app/models/classifier.py << 'EOF'
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)
classifier = None

def load_classifier():
    global classifier
    if classifier is None:
        try:
            classifier = pipeline(
                "text-classification",
                model="aditya96k/policy-clause-classifier"
            )
        except Exception as e:
            logger.warning(f"Classifier load error: {e}")
            classifier = None
    return classifier

def classify_clause(text: str) -> list:
    try:
        clf = load_classifier()
        if clf:
            return clf(text)
        return [{"label": "UNKNOWN"}]
    except:
        return [{"label": "UNKNOWN"}]
EOF

# Create Schemas
cat > app/schemas/claim_schema.py << 'EOF'
from pydantic import BaseModel

class ClaimRequest(BaseModel):
    query: str
EOF

cat > app/schemas/risk_schema.py << 'EOF'
from pydantic import BaseModel
from typing import Optional, Dict

class RiskRequest(BaseModel):
    applicant_data: Dict
    policy_type: str = "life"
    coverage_amount: Optional[float] = None
EOF

cat > app/schemas/response_schema.py << 'EOF'
from pydantic import BaseModel
from typing import Any

class ClaimResponse(BaseModel):
    result: Any

class RiskResponse(BaseModel):
    result: Any

class ChatResponse(BaseModel):
    result: str

class WhatIfResponse(BaseModel):
    result: Any
EOF

echo "All files created successfully!"

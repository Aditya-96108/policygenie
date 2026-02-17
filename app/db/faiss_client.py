# app/db/faiss_client.py
# FAISS Client for Hybrid Search - CORRECTED VERSION
# Fixes:
# - Removed async from methods (sync for performance and simplicity).
# - Improved index creation with proper training.
# - Better error handling in search.
# - Persistent storage with pickle for ID mapping.

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
        self.dimension = 3072  # text-embedding-3-small dimension
        self.index_path = getattr(settings, 'faiss_index_path', "chroma_db/faiss_index")
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            index_file = f"{self.index_path}.index"
            map_file = f"{self.index_path}.map"
            if os.path.exists(index_file) and os.path.exists(map_file):
                self.index = faiss.read_index(index_file)
                with open(map_file, 'rb') as f:
                    self.id_map = pickle.load(f)
                logger.info("Loaded existing FAISS index")
            else:
                # Create IVF index for scalability
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)  # 100 clusters
                self.index.nprobe = 10
                logger.info("Created new FAISS index")
        except Exception as e:
            logger.warning(f"FAISS init fallback: {e}")
            self.index = faiss.IndexFlatL2(self.dimension)
    
    def add_vectors(self, vectors: np.ndarray, ids: List[str]):
        """Add vectors to FAISS index."""
        try:
            if vectors.shape[1] != self.dimension:
                logger.error(f"Vector dimension mismatch: {vectors.shape[1]} vs {self.dimension}")
                return
            if self.index.ntotal == 0:
                self.index.train(vectors.astype('float32'))
            start_idx = self.index.ntotal
            self.index.add(vectors.astype('float32'))
            for i, doc_id in enumerate(ids):
                self.id_map[start_idx + i] = doc_id
            self._save_index()
            logger.debug(f"Added {len(ids)} vectors to FAISS")
        except Exception as e:
            logger.error(f"Add vectors error: {e}")
    
    def search(self, query_vectors: np.ndarray, k: int = 5) -> List[List[str]]:
        """Search FAISS for similar vectors."""
        try:
            if self.index.ntotal == 0:
                return [[]]
            distances, indices = self.index.search(query_vectors.astype('float32'), k)
            results = []
            for idx_list in indices:
                doc_ids = [self.id_map.get(int(idx), "") for idx in idx_list if idx in self.id_map]
                results.append(doc_ids)
            return results
        except Exception as e:
            logger.error(f"FAISS search error: {e}")
            return [[]]
    
    def _save_index(self):
        """Save index and ID map to disk."""
        try:
            index_file = f"{self.index_path}.index"
            map_file = f"{self.index_path}.map"
            faiss.write_index(self.index, index_file)
            with open(map_file, 'wb') as f:
                pickle.dump(self.id_map, f)
            logger.debug("Saved FAISS index")
        except Exception as e:
            logger.error(f"Save index error: {e}")

# Singleton
faiss_index = FAISSIndex()
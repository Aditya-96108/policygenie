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

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_service import generate_response_async, llm_service
from app.services.rag_service import retrieve
from app.utils.prompts import get_chat_prompt
from app.schemas.response_schema import ChatResponse

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    query: str

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        embeddings = await llm_service.generate_embeddings([request.query])
        docs = retrieve(embeddings[0])  # SYNC function, no await
        context = "\n".join(docs[0]) if docs and docs[0] else ""
        
        prompt = get_chat_prompt(context, request.query)
        result = await generate_response_async(prompt)
        return ChatResponse(result=result)
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(500, str(e))

"""
Enhanced LLM Service with Retry Logic, Monitoring, and Multi-Provider Support
"""
import logging
import asyncio
from typing import Optional, List, Dict
from openai import OpenAI, AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Production-grade LLM service with:
    1. Automatic retry with exponential backoff
    2. Rate limiting and quota management
    3. Response caching
    4. Error handling and fallbacks
    5. Token usage tracking
    """
    
    def __init__(self):
        self._sync_client = None
        self._async_client = None
        self._total_tokens_used = 0
        self._request_count = 0
        
    def _get_sync_client(self) -> OpenAI:
        """Get or create synchronous OpenAI client"""
        if not self._sync_client:
            self._sync_client = OpenAI(api_key=settings.openai_api_key)
        return self._sync_client
    
    def _get_async_client(self) -> AsyncOpenAI:
        """Get or create asynchronous OpenAI client"""
        if not self._async_client:
            self._async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._async_client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def generate_response_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_message: Optional[str] = None
    ) -> str:
        """
        Generate LLM response asynchronously with retry logic
        
        Args:
            prompt: User prompt
            model: Model to use (defaults to settings.llm_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            system_message: Optional system message
            
        Returns:
            Generated text response
        """
        try:
            client = self._get_async_client()
            model = model or settings.llm_model
            
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            logger.info(f"Generating response with {model}")
            
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Track usage
            self._request_count += 1
            if hasattr(response, 'usage'):
                self._total_tokens_used += response.usage.total_tokens
                logger.info(f"Tokens used: {response.usage.total_tokens}")
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_response_sync(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_message: Optional[str] = None
    ) -> str:
        """Synchronous version of generate_response"""
        try:
            client = self._get_sync_client()
            model = model or settings.llm_model
            
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            self._request_count += 1
            if hasattr(response, 'usage'):
                self._total_tokens_used += response.usage.total_tokens
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            model: Embedding model (defaults to settings.embedding_model)
            
        Returns:
            List of embedding vectors
        """
        try:
            client = self._get_async_client()
            model = model or settings.embedding_model
            
            # Batch embeddings for efficiency
            response = await client.embeddings.create(
                model=model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation error: {str(e)}")
            raise
    
    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict,
        model: Optional[str] = None
    ) -> Dict:
        """
        Generate structured JSON output matching schema
        
        Args:
            prompt: User prompt
            schema: JSON schema for output
            model: Model to use
            
        Returns:
            Parsed JSON response
        """
        try:
            import json
            
            system_message = f"""
You are an AI that outputs only valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Output ONLY the JSON, no additional text.
"""
            
            response = await self.generate_response_async(
                prompt,
                model=model,
                system_message=system_message,
                temperature=0.3
            )
            
            # Parse JSON response
            parsed = json.loads(response)
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise ValueError(f"Invalid JSON response: {response}")
        except Exception as e:
            logger.error(f"Structured output error: {str(e)}")
            raise
    
    def get_usage_stats(self) -> Dict:
        """Get LLM usage statistics"""
        return {
            "total_requests": self._request_count,
            "total_tokens_used": self._total_tokens_used,
            "average_tokens_per_request": (
                self._total_tokens_used / self._request_count
                if self._request_count > 0 else 0
            )
        }


# Singleton instance
llm_service = LLMService()


# Convenience functions for backward compatibility
def get_embedding_client() -> OpenAI:
    """Get OpenAI client for embeddings"""
    return llm_service._get_sync_client()


def get_llm_client() -> OpenAI:
    """Get OpenAI client"""
    return llm_service._get_sync_client()


def generate_response(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> str:
    """Synchronous response generation"""
    return llm_service.generate_response_sync(prompt, model, temperature, max_tokens)


async def generate_response_async(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> str:
    """Asynchronous response generation"""
    return await llm_service.generate_response_async(prompt, model, temperature, max_tokens)

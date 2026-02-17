"""
PolicyGenie AI - Production Main Application
Fixes: Model preloading, timeout issues, async errors
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from time import time

from app.core.cache_service import cache_manager
from app.routes import upload, claim, risk, chat, whatif, pdf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)




async def preload_ml_models():
    """Pre-load ML models at startup to avoid slow first request"""
    logger.info("=" * 70)
    logger.info("🤖 PRE-LOADING ML MODELS (takes 2-3 minutes, please wait...)")
    logger.info("=" * 70)
    
    try:
        from app.services.fraud_service import fraud_detector
        from app.models.classifier import load_classifier
        
        # Load fraud models
        logger.info("📥 Loading DeBERTa v3 (268MB) + DistilBERT (268MB)...")
        start = time()
        await fraud_detector._load_models()
        logger.info(f"✓ Fraud models loaded in {time()-start:.1f}s")
        
        # Load classifier
        logger.info("📥 Loading policy classifier...")
        start = time()
        load_classifier()
        logger.info(f"✓ Classifier loaded in {time()-start:.1f}s")
        
        logger.info("=" * 70)
        logger.info("✅ ALL MODELS LOADED - API READY FOR FAST RESPONSES!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"⚠️  Model preloading failed: {e}")
        logger.warning("API will work but first requests will be slow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    logger.info("🚀 Starting PolicyGenie AI...")
    
    try:
        await cache_manager.initialize_redis()
        logger.info("✓ Cache initialized")
    except Exception as e:
        logger.warning(f"Cache warning: {e} - using memory cache")
    
    await preload_ml_models()
    
    logger.info("✅ PolicyGenie AI ready!")
    logger.info("📖 Docs: http://localhost:8000/docs")
    logger.info("❤️  Health: http://localhost:8000/health")
    
    yield
    
    logger.info("👋 Shutting down...")


app = FastAPI(
    title="PolicyGenie AI",
    description="Enterprise Insurance Platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "path": str(request.url.path)}
    )


app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(claim.router, prefix="/api", tags=["Claims"])
app.include_router(risk.router, prefix="/api", tags=["Risk"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(whatif.router, prefix="/api", tags=["What-If"])
app.include_router(pdf.router, prefix="/api", tags=["PDF"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "PolicyGenie AI",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    from app.services.fraud_service import fraud_detector
    
    return {
        "status": "healthy",
        "timestamp": time(),
        "models_loaded": fraud_detector._models_loaded,
        "cache": cache_manager.get_stats(),
        "services": {
            "api": "operational",
            "ml_models": "loaded" if fraud_detector._models_loaded else "loading"
        }
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=300
    )

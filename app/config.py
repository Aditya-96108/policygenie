from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Production-grade configuration management with validation"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Keys (Required)
    openai_api_key: str = Field(..., min_length=20)
    anthropic_api_key: Optional[str] = None
    
    # Database Paths
    chroma_path: str = "data/chroma_db"
    faiss_index_path: str = "data/faiss_index"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    
    # Security
    max_file_size: int = 10485760
    allowed_extensions: str = "pdf"
    secret_key: str = Field(default="dev-secret-key-change-in-prod")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    cache_ttl: int = 3600
    
    # AI Models
    embedding_model: str = "text-embedding-3-large"
    llm_model: str = "gpt-4o"
    fraud_detection_model: str = "microsoft/deberta-v3-large"
    risk_scoring_model: str = "ProsusAI/finbert"
    sentiment_model: str = "distilbert-base-uncased-finetuned-sst-2-english"
    
    # Thresholds
    fraud_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    anomaly_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    risk_high_threshold: int = Field(default=80, ge=0, le=100)
    risk_medium_threshold: int = Field(default=50, ge=0, le=100)
    
    # Performance
    max_workers: int = Field(default=4, ge=1)
    batch_size: int = Field(default=32, ge=1)
    enable_caching: bool = True
    enable_monitoring: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Business Rules
    auto_approve_threshold: int = Field(default=30, ge=0, le=100)
    auto_reject_threshold: int = Field(default=85, ge=0, le=100)
    requires_human_review_min: int = Field(default=70, ge=0, le=100)
    requires_human_review_max: int = Field(default=85, ge=0, le=100)
    
    # Advanced Features
    enable_explainable_ai: bool = True
    enable_bias_detection: bool = True
    enable_real_time_monitoring: bool = True
    enable_predictive_analytics: bool = True
    
    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, v: str) -> list:
        return [ext.strip() for ext in v.split(",")]
    
    @property
    def is_production(self) -> bool:
        return self.secret_key != "dev-secret-key-change-in-prod"


# Singleton instance
settings = Settings()

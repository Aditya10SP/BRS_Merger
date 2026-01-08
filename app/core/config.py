"""
Configuration settings for the BRS Consolidator system.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    API_TITLE: str = "GenAI BRS Consolidator"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Enterprise-grade BRS consolidation using controlled RAG"
    
    # LLM Configuration
    LLM_PROVIDER: str = "ollama"  # EXCLUSIVE: Remote Ollama only
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "https://ollama.icicilabs.com/v1"  # Remote Ollama endpoint
    
    # Model Configuration
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MODEL: str = "deepseek-coder-v2:latest"  # Remote Ollama model - EXCLUSIVE USE
    LLM_TEMPERATURE: float = 0.1  # Low temperature for deterministic outputs
    LLM_MAX_TOKENS: int = 2000
    LLM_TIMEOUT: float = 300.0  # 5 minute timeout for remote Ollama requests
    
    # Vector Store Configuration
    VECTOR_DB_TYPE: str = "chroma"  # chroma or faiss
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    CHROMA_COLLECTION_BRS: str = "brs_chunks"
    CHROMA_COLLECTION_CR: str = "cr_deltas"
    
    # Retrieval Configuration
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Processing Configuration
    MAX_CHUNK_SIZE: int = 1000  # characters
    CHUNK_OVERLAP: int = 100
    
    # File paths
    DATA_DIR: str = "./data"
    UPLOAD_DIR: str = "./data/uploads"
    OUTPUT_DIR: str = "./data/outputs"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

"""Configuration settings for Newspaper RAG system."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """System configuration."""
    
    # Application settings
    APP_NAME = "Newspaper RAG"
    APP_VERSION = "1.0.0"
    
    # Vector database settings
    VECTOR_DB_PROVIDER = os.getenv("VECTOR_DB_PROVIDER", "pinecone")  # pinecone or weaviate
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "newspaper-rag")
    
    # Embedding settings
    EMBEDDING_MODEL = "multilingual-e5-large"  # Pinecone-hosted
    EMBEDDING_DIMENSION = 1024
    
    # Chunking settings
    CHUNK_SIZE = 350  # words (safe under 507 token limit)
    CHUNK_OVERLAP = 75  # words
    
    # Search settings
    MAX_SEARCH_RESULTS = 20
    RELEVANCE_THRESHOLD = 0.7
    BM25_WEIGHT = 0.3  # Weight for BM25 in hybrid search
    
    # LLM settings (for response generation)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # gemini or openai
    
    # Model settings based on provider
    if LLM_PROVIDER == "gemini":
        LLM_MODEL = "gemini-2.5-pro"  # Latest Gemini Pro model
        LLM_TEMPERATURE = 0.7
        LLM_MAX_TOKENS = 8192  # Gemini 2.5 Pro supports longer outputs
    else:
        LLM_MODEL = "gpt-3.5-turbo"
        LLM_TEMPERATURE = 0.7
        LLM_MAX_TOKENS = 1500
    
    # Database settings (for metadata storage)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///newspaper_metadata.db")
    
    # Processing settings
    BATCH_SIZE = 100
    MAX_WORKERS = 4
    
    # UI settings
    STREAMLIT_THEME = "light"
    MAX_DATE_RANGE_DAYS = 36500  # 100 years
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "newspaper_rag.log"
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        errors = []
        
        if cls.VECTOR_DB_PROVIDER == "pinecone" and not cls.PINECONE_API_KEY:
            errors.append("PINECONE_API_KEY is required when using Pinecone")
        
        # OpenAI is now optional since we can use other LLMs
        # if not cls.OPENAI_API_KEY:
        #     errors.append("OPENAI_API_KEY is required for response generation")
        
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
        
        return True

config = Config()
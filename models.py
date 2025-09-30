"""Data models for Newspaper RAG system."""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

@dataclass
class NewspaperMetadata:
    """Metadata for a newspaper document."""
    newspaper_name: str
    publication_date: date
    page_number: Optional[int] = None
    section: Optional[str] = None
    source_url: Optional[str] = None
    ocr_quality_score: Optional[float] = None
    language: str = "en"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "newspaper_name": self.newspaper_name,
            "publication_date": self.publication_date.isoformat(),
            "page_number": self.page_number,
            "section": self.section,
            "source_url": self.source_url,
            "ocr_quality_score": self.ocr_quality_score,
            "language": self.language
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewspaperMetadata":
        """Create from dictionary."""
        data = data.copy()
        if isinstance(data.get("publication_date"), str):
            data["publication_date"] = date.fromisoformat(data["publication_date"])
        return cls(**data)


@dataclass
class DocumentChunk:
    """A chunk of newspaper text with metadata."""
    chunk_id: str
    content: str
    newspaper_metadata: NewspaperMetadata
    chunk_index: int
    start_char: int
    end_char: int
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "newspaper_metadata": self.newspaper_metadata.to_dict(),
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "embedding": self.embedding
        }


@dataclass
class SearchQuery:
    """Search query with filters."""
    query_text: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    newspaper_names: Optional[List[str]] = None
    max_results: int = 20
    relevance_threshold: float = 0.7
    search_type: str = "hybrid"  # hybrid, semantic, or keyword
    
    def get_date_filter(self) -> Optional[Dict[str, Any]]:
        """Get date filter for vector database."""
        if not self.start_date and not self.end_date:
            return None
        
        filter_dict = {}
        if self.start_date:
            filter_dict["publication_date"] = {"$gte": self.start_date.isoformat()}
        if self.end_date:
            if "publication_date" in filter_dict:
                filter_dict["publication_date"]["$lte"] = self.end_date.isoformat()
            else:
                filter_dict["publication_date"] = {"$lte": self.end_date.isoformat()}
        
        return filter_dict


@dataclass
class SearchResult:
    """A search result with relevance score."""
    chunk: DocumentChunk
    relevance_score: float
    highlights: Optional[List[str]] = None
    
    def format_citation(self) -> str:
        """Format as citation."""
        meta = self.chunk.newspaper_metadata
        return (f"{meta.newspaper_name}, "
                f"{meta.publication_date.strftime('%B %d, %Y')}, "
                f"p. {meta.page_number if meta.page_number else 'N/A'}")


@dataclass
class ProcessingStats:
    """Statistics from document processing."""
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    total_words: int = 0
    date_range: Optional[tuple[date, date]] = None
    newspapers: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "total_chunks": self.total_chunks,
            "total_words": self.total_words,
            "date_range": [d.isoformat() for d in self.date_range] if self.date_range else None,
            "newspapers": self.newspapers,
            "processing_time_seconds": self.processing_time_seconds
        }
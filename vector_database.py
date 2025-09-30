"""Vector database handler for newspaper search."""

import os
from typing import List, Dict, Any, Optional
from datetime import date
import numpy as np
from loguru import logger
import pickle
from pathlib import Path

from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import pinecone

from models import DocumentChunk, SearchQuery, SearchResult
from config import config


class VectorDatabase:
    """Handles vector storage and retrieval."""
    
    def __init__(self):
        # Initialize embedding model
        logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        self.encoder = SentenceTransformer(config.EMBEDDING_MODEL)
        
        # Initialize Pinecone
        if config.VECTOR_DB_PROVIDER == "pinecone":
            self._init_pinecone()
        else:
            raise ValueError(f"Unsupported vector DB provider: {config.VECTOR_DB_PROVIDER}")
        
        # BM25 index for hybrid search
        self.bm25_index = None
        self.bm25_docs = []
        self.bm25_metadata = []
        
    def _init_pinecone(self):
        """Initialize Pinecone connection."""
        pinecone.init(
            api_key=config.PINECONE_API_KEY,
            environment=config.PINECONE_ENVIRONMENT
        )
        
        # Create index if it doesn't exist
        if config.PINECONE_INDEX_NAME not in pinecone.list_indexes():
            logger.info(f"Creating Pinecone index: {config.PINECONE_INDEX_NAME}")
            pinecone.create_index(
                config.PINECONE_INDEX_NAME,
                dimension=config.EMBEDDING_DIMENSION,
                metric="cosine"
            )
        
        self.index = pinecone.Index(config.PINECONE_INDEX_NAME)
        logger.info("Connected to Pinecone")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks."""
        embeddings = self.encoder.encode(texts, show_progress_bar=True)
        return embeddings.tolist()
    
    def index_chunks(self, chunks: List[DocumentChunk], batch_size: int = config.BATCH_SIZE):
        """Index document chunks in vector database."""
        logger.info(f"Indexing {len(chunks)} chunks")
        
        # Prepare data for BM25
        self.bm25_docs = []
        self.bm25_metadata = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Extract texts
            texts = [chunk.content for chunk in batch]
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            
            # Prepare vectors for Pinecone
            vectors = []
            for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                # Prepare metadata
                metadata = {
                    "content": chunk.content,
                    "newspaper_name": chunk.newspaper_metadata.newspaper_name,
                    "publication_date": chunk.newspaper_metadata.publication_date.isoformat(),
                    "page_number": chunk.newspaper_metadata.page_number,
                    "section": chunk.newspaper_metadata.section,
                    "chunk_index": chunk.chunk_index,
                    "source_url": chunk.newspaper_metadata.source_url
                }
                
                vectors.append((chunk.chunk_id, embedding, metadata))
                
                # Add to BM25 data
                self.bm25_docs.append(chunk.content.lower().split())
                self.bm25_metadata.append(chunk)
            
            # Upsert to Pinecone
            self.index.upsert(vectors)
            logger.info(f"Indexed batch {i//batch_size + 1}/{len(chunks)//batch_size + 1}")
        
        # Build BM25 index
        logger.info("Building BM25 index")
        self.bm25_index = BM25Okapi(self.bm25_docs)
        
        logger.info("Indexing complete")
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for relevant chunks."""
        if query.search_type == "hybrid":
            return self._hybrid_search(query)
        elif query.search_type == "semantic":
            return self._semantic_search(query)
        elif query.search_type == "keyword":
            return self._keyword_search(query)
        else:
            raise ValueError(f"Unknown search type: {query.search_type}")
    
    def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform semantic search using embeddings."""
        # Generate query embedding
        query_embedding = self.encoder.encode(query.query_text).tolist()
        
        # Build filter
        filter_dict = {}
        
        # Date filter
        if query.start_date:
            filter_dict["publication_date"] = {"$gte": query.start_date.isoformat()}
        if query.end_date:
            if "publication_date" in filter_dict:
                filter_dict["publication_date"]["$lte"] = query.end_date.isoformat()
            else:
                filter_dict["publication_date"] = {"$lte": query.end_date.isoformat()}
        
        # Newspaper filter
        if query.newspaper_names:
            filter_dict["newspaper_name"] = {"$in": query.newspaper_names}
        
        # Search Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=query.max_results,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        # Convert to SearchResult objects
        search_results = []
        for match in results.matches:
            if match.score >= query.relevance_threshold:
                # Reconstruct metadata
                metadata = NewspaperMetadata(
                    newspaper_name=match.metadata["newspaper_name"],
                    publication_date=date.fromisoformat(match.metadata["publication_date"]),
                    page_number=match.metadata.get("page_number"),
                    section=match.metadata.get("section"),
                    source_url=match.metadata.get("source_url")
                )
                
                # Reconstruct chunk
                chunk = DocumentChunk(
                    chunk_id=match.id,
                    content=match.metadata["content"],
                    newspaper_metadata=metadata,
                    chunk_index=match.metadata["chunk_index"],
                    start_char=0,  # Not stored in metadata
                    end_char=len(match.metadata["content"])
                )
                
                search_results.append(SearchResult(
                    chunk=chunk,
                    relevance_score=match.score
                ))
        
        return search_results
    
    def _keyword_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform keyword search using BM25."""
        if not self.bm25_index:
            logger.warning("BM25 index not available, falling back to semantic search")
            return self._semantic_search(query)
        
        # Tokenize query
        query_tokens = query.query_text.lower().split()
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)
        
        # Get top results
        top_indices = np.argsort(scores)[::-1][:query.max_results * 2]  # Get extra for filtering
        
        # Filter and create results
        search_results = []
        for idx in top_indices:
            if len(search_results) >= query.max_results:
                break
            
            chunk = self.bm25_metadata[idx]
            
            # Apply date filter
            if query.start_date and chunk.newspaper_metadata.publication_date < query.start_date:
                continue
            if query.end_date and chunk.newspaper_metadata.publication_date > query.end_date:
                continue
            
            # Apply newspaper filter
            if query.newspaper_names and chunk.newspaper_metadata.newspaper_name not in query.newspaper_names:
                continue
            
            # Normalize BM25 score to 0-1 range
            normalized_score = min(scores[idx] / 10.0, 1.0)
            
            if normalized_score >= query.relevance_threshold:
                search_results.append(SearchResult(
                    chunk=chunk,
                    relevance_score=normalized_score
                ))
        
        return search_results
    
    def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform hybrid search combining semantic and keyword search."""
        # Get results from both methods
        semantic_results = self._semantic_search(query)
        keyword_results = self._keyword_search(query)
        
        # Combine results with weighted scores
        result_map = {}
        
        # Add semantic results
        for result in semantic_results:
            result_map[result.chunk.chunk_id] = {
                "chunk": result.chunk,
                "semantic_score": result.relevance_score * (1 - config.BM25_WEIGHT),
                "keyword_score": 0.0
            }
        
        # Add keyword results
        for result in keyword_results:
            if result.chunk.chunk_id in result_map:
                result_map[result.chunk.chunk_id]["keyword_score"] = result.relevance_score * config.BM25_WEIGHT
            else:
                result_map[result.chunk.chunk_id] = {
                    "chunk": result.chunk,
                    "semantic_score": 0.0,
                    "keyword_score": result.relevance_score * config.BM25_WEIGHT
                }
        
        # Calculate combined scores and create final results
        final_results = []
        for chunk_id, data in result_map.items():
            combined_score = data["semantic_score"] + data["keyword_score"]
            if combined_score >= query.relevance_threshold:
                final_results.append(SearchResult(
                    chunk=data["chunk"],
                    relevance_score=combined_score
                ))
        
        # Sort by combined score
        final_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return final_results[:query.max_results]
    
    def save_bm25_index(self, filepath: Path):
        """Save BM25 index to file."""
        if self.bm25_index:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'bm25_index': self.bm25_index,
                    'bm25_docs': self.bm25_docs,
                    'bm25_metadata': self.bm25_metadata
                }, f)
            logger.info(f"Saved BM25 index to {filepath}")
    
    def load_bm25_index(self, filepath: Path):
        """Load BM25 index from file."""
        if filepath.exists():
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.bm25_index = data['bm25_index']
                self.bm25_docs = data['bm25_docs']
                self.bm25_metadata = data['bm25_metadata']
            logger.info(f"Loaded BM25 index from {filepath}")


# Import NewspaperMetadata to avoid circular import
from models import NewspaperMetadata
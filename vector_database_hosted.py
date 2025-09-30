"""Vector database interface for Pinecone with hosted embeddings."""

import os
from typing import List, Dict, Any, Optional
from datetime import date
import time
from loguru import logger
from tqdm import tqdm
import pickle

import pinecone
from pinecone import Pinecone, ServerlessSpec
import numpy as np
from rank_bm25 import BM25Okapi

from models import DocumentChunk, SearchQuery, SearchResult, NewspaperMetadata


class VectorDatabaseHosted:
    """Vector database using Pinecone-hosted embeddings."""
    
    def __init__(self):
        """Initialize Pinecone connection."""
        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "newspaper-rag")
        
        # Connect to index
        self.index = self.pc.Index(self.index_name)
        
        # Get index stats
        stats = self.index.describe_index_stats()
        logger.info(f"Connected to Pinecone index '{self.index_name}'")
        logger.info(f"Index stats: {stats}")
        
        # BM25 components (still needed for hybrid search)
        self.bm25 = None
        self.chunks = []
        self.chunk_texts = []
        
    def prepare_chunks_for_upsert(self, chunks: List[DocumentChunk]) -> List[Dict[str, Any]]:
        """Prepare chunks for upserting to Pinecone with hosted embeddings."""
        vectors = []
        
        for chunk in chunks:
            # Create metadata including the text field for embedding
            metadata = {
                "newspaper_name": chunk.newspaper_metadata.newspaper_name,
                "publication_date": chunk.newspaper_metadata.publication_date.isoformat(),
                "section": chunk.newspaper_metadata.section or "",
                "page_number": chunk.newspaper_metadata.page_number or 0,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "text": chunk.content  # Include text in metadata for hosted embeddings
            }
            
            # For hosted embeddings with inference API, format is different
            vector_data = {
                "id": chunk.chunk_id,
                "metadata": metadata
            }
            
            vectors.append(vector_data)
        
        return vectors
    
    def index_chunks(self, chunks: List[DocumentChunk], batch_size: int = 100):
        """Index chunks to Pinecone with hosted embeddings."""
        logger.info(f"Indexing {len(chunks)} chunks to Pinecone...")
        
        # Store chunks for BM25
        self.chunks = chunks
        self.chunk_texts = [chunk.content for chunk in chunks]
        
        # Process in batches
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        with tqdm(total=len(chunks), desc="Indexing to Pinecone") as pbar:
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                
                try:
                    # Step 1: Extract texts for embedding
                    texts_to_embed = [chunk.content for chunk in batch_chunks]
                    
                    # Step 2: Get embeddings from Pinecone inference API
                    embedding_response = self.pc.inference.embed(
                        model="multilingual-e5-large",
                        inputs=texts_to_embed,
                        parameters={"input_type": "passage", "truncate": "END"}
                    )
                    
                    # Step 3: Prepare vectors for upsert
                    vectors_to_upsert = []
                    for j, chunk in enumerate(batch_chunks):
                        metadata = {
                            "text": chunk.content,
                            "newspaper_name": chunk.newspaper_metadata.newspaper_name,
                            "publication_date": chunk.newspaper_metadata.publication_date.isoformat(),
                            "section": chunk.newspaper_metadata.section or "",
                            "page_number": chunk.newspaper_metadata.page_number or 0,
                            "chunk_index": chunk.chunk_index,
                            "start_char": chunk.start_char,
                            "end_char": chunk.end_char,
                        }
                        
                        vectors_to_upsert.append({
                            "id": chunk.chunk_id,
                            "values": embedding_response[j].values,
                            "metadata": metadata
                        })
                    
                    # Step 4: Upsert to Pinecone with retry logic
                    max_retries = 3
                    retry_delay = 1.0
                    
                    for attempt in range(max_retries):
                        try:
                            self.index.upsert(vectors=vectors_to_upsert)
                            pbar.update(len(batch_chunks))
                            break
                        except Exception as e:
                            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                                # Rate limit error - wait longer
                                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                                logger.warning(f"Rate limit hit, waiting {wait_time:.1f} seconds...")
                                time.sleep(wait_time)
                                if attempt == max_retries - 1:
                                    raise  # Re-raise if final attempt
                            else:
                                # Other error - re-raise immediately
                                raise
                    
                    # Calculate delay based on batch size to stay under 1M tokens/minute
                    # Estimate ~200 tokens per chunk on average
                    tokens_in_batch = len(batch_chunks) * 200
                    # Stay at 80% of rate limit (800k tokens/minute)
                    target_tokens_per_minute = 800000
                    min_delay = (tokens_in_batch / target_tokens_per_minute) * 60
                    
                    # Use at least 1 second delay, or calculated delay, whichever is larger
                    delay = max(1.0, min_delay)
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error uploading batch {i//batch_size + 1}: {e}")
                    raise
        
        # Build BM25 index
        logger.info("Building BM25 index...")
        tokenized_texts = [text.lower().split() for text in self.chunk_texts]
        self.bm25 = BM25Okapi(tokenized_texts)
        
        logger.info(f"Successfully indexed {len(chunks)} chunks")
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for documents using hosted embeddings."""
        
        # Build metadata filter
        metadata_filter = {}
        
        # Note: Pinecone doesn't support date filtering on string fields
        # We'll filter results after retrieval instead
        
        if query.newspaper_names:
            metadata_filter["newspaper_name"] = {"$in": query.newspaper_names}
        
        results = []
        
        if query.search_type in ["semantic", "hybrid"]:
            # For hosted embeddings, we need to embed the query first
            query_embedding = self.pc.inference.embed(
                model="multilingual-e5-large",
                inputs=[query.query_text],
                parameters={"input_type": "query", "truncate": "END"}
            )
            
            # Query with the embedding
            semantic_results = self.index.query(
                vector=query_embedding[0].values,
                top_k=query.max_results * 2 if query.search_type == "hybrid" else query.max_results,
                filter=metadata_filter if metadata_filter else None,
                include_metadata=True
            )
            
            # Process semantic results
            for match in semantic_results.matches:
                # Reconstruct chunk from metadata
                metadata = match.metadata
                
                # Parse date from metadata
                try:
                    pub_date = date.fromisoformat(metadata.get('publication_date', ''))
                    
                    # Apply date filtering
                    if query.start_date and pub_date < query.start_date:
                        continue
                    if query.end_date and pub_date > query.end_date:
                        continue
                        
                except:
                    # Skip if date parsing fails
                    continue
                
                # Create chunk from metadata
                from models import NewspaperMetadata
                newspaper_meta = NewspaperMetadata(
                    newspaper_name=metadata.get('newspaper_name', 'Unknown'),
                    publication_date=pub_date,
                    page_number=metadata.get('page_number'),
                    section=metadata.get('section')
                )
                
                chunk = DocumentChunk(
                    chunk_id=match.id,
                    content=metadata.get('text', ''),
                    newspaper_metadata=newspaper_meta,
                    chunk_index=metadata.get('chunk_index', 0),
                    start_char=metadata.get('start_char', 0),
                    end_char=metadata.get('end_char', 0)
                )
                
                result = SearchResult(
                    chunk=chunk,
                    relevance_score=match.score
                )
                results.append(result)
        
        if query.search_type in ["keyword", "hybrid"] and self.bm25:
            # BM25 keyword search (local)
            query_tokens = query.query_text.lower().split()
            bm25_scores = self.bm25.get_scores(query_tokens)
            
            # Get top results from BM25
            top_indices = np.argsort(bm25_scores)[::-1][:query.max_results]
            
            for idx in top_indices:
                if bm25_scores[idx] > 0:
                    chunk = self.chunks[idx]
                    
                    # Check date filter
                    if query.start_date and chunk.newspaper_metadata.publication_date < query.start_date:
                        continue
                    if query.end_date and chunk.newspaper_metadata.publication_date > query.end_date:
                        continue
                    
                    # Normalize BM25 score
                    normalized_score = min(bm25_scores[idx] / 10.0, 1.0)
                    
                    result = SearchResult(
                        chunk=chunk,
                        relevance_score=normalized_score
                    )
                    results.append(result)
        
        # Combine and deduplicate results for hybrid search
        if query.search_type == "hybrid":
            # Deduplicate by chunk_id, keeping highest score
            seen = {}
            for result in results:
                chunk_id = result.chunk.chunk_id
                if chunk_id not in seen or result.relevance_score > seen[chunk_id].relevance_score:
                    seen[chunk_id] = result
            results = list(seen.values())
        
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Apply relevance threshold and limit
        results = [r for r in results if r.relevance_score >= query.relevance_threshold]
        results = results[:query.max_results]
        
        return results
    
    def save_bm25_index(self, filepath: str):
        """Save BM25 index and chunks to disk."""
        data = {
            'chunks': self.chunks,
            'chunk_texts': self.chunk_texts,
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Saved BM25 index to {filepath}")
    
    def load_bm25_index(self, filepath: str):
        """Load BM25 index and chunks from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.chunks = data['chunks']
        self.chunk_texts = data['chunk_texts']
        
        # Rebuild BM25
        tokenized_texts = [text.lower().split() for text in self.chunk_texts]
        self.bm25 = BM25Okapi(tokenized_texts)
        
        logger.info(f"Loaded BM25 index from {filepath}")
    
    def delete_all_vectors(self):
        """Delete all vectors from the index (useful for cleanup)."""
        try:
            self.index.delete(delete_all=True)
            logger.info("Deleted all vectors from index")
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
"""Simple search test to understand the search behavior"""

from datetime import date
from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path

# Test BM25 functionality first
print("Testing BM25 functionality...")
try:
    import pickle
    from rank_bm25 import BM25Okapi
    
    bm25_path = Path("processed_data/bm25_index_hosted.pkl")
    if bm25_path.exists():
        with open(bm25_path, 'rb') as f:
            data = pickle.load(f)
        
        chunks = data['chunks']
        chunk_texts = data['chunk_texts']
        
        print(f"Loaded {len(chunks)} chunks from BM25 index")
        
        # Build BM25
        tokenized_texts = [text.lower().split() for text in chunk_texts]
        bm25 = BM25Okapi(tokenized_texts)
        
        # Test femininity-related queries
        test_queries = [
            "femininity",
            "feminine", 
            "woman",
            "women",
            "communist women",
            "female workers"
        ]
        
        for query_text in test_queries:
            query_tokens = query_text.lower().split()
            bm25_scores = bm25.get_scores(query_tokens)
            
            # Get top 5 results
            import numpy as np
            top_indices = np.argsort(bm25_scores)[::-1][:5]
            top_scores = [bm25_scores[idx] for idx in top_indices]
            
            print(f"\n--- BM25 Results for '{query_text}' ---")
            print(f"Max score: {max(bm25_scores):.4f}")
            print(f"Results with score > 0: {sum(1 for s in bm25_scores if s > 0)}")
            
            if max(bm25_scores) > 0:
                print("Top 3 matches:")
                for i, (idx, score) in enumerate(zip(top_indices[:3], top_scores[:3])):
                    if score > 0:
                        chunk = chunks[idx]
                        print(f"  {i+1}. Score: {score:.4f}")
                        print(f"      Date: {chunk.newspaper_metadata.publication_date}")
                        print(f"      Content: {chunk.content[:100]}...")
                        print()
            
    else:
        print("BM25 index file not found at processed_data/bm25_index_hosted.pkl")
        
except Exception as e:
    print(f"Error loading BM25 index: {e}")
    import traceback
    traceback.print_exc()

# Also test what happens with embedding search at different thresholds
print(f"\n{'='*60}")
print("TESTING EMBEDDING SEARCH")
print(f"{'='*60}")

try:
    from vector_database_hosted import VectorDatabaseHosted
    from models import SearchQuery
    
    print("Initializing vector database...")
    vector_db = VectorDatabaseHosted()
    
    # Load BM25 if available
    if bm25_path.exists():
        vector_db.load_bm25_index(bm25_path)
    
    # Test with very low threshold first to see if any matches exist
    query = SearchQuery(
        query_text="women",
        search_type="semantic",
        max_results=5,
        relevance_threshold=0.1,  # Very low threshold
        start_date=date(1924, 1, 1),
        end_date=date(1958, 12, 31)
    )
    
    print(f"Testing semantic search for 'women' with threshold 0.1...")
    results = vector_db.search(query)
    print(f"Found {len(results)} results")
    
    if results:
        print("Score distribution:")
        scores = [r.relevance_score for r in results]
        print(f"  Min: {min(scores):.4f}, Max: {max(scores):.4f}, Avg: {sum(scores)/len(scores):.4f}")
        
        print("Top 3 results:")
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. Score: {result.relevance_score:.4f}")
            print(f"      Date: {result.chunk.newspaper_metadata.publication_date}")
            print(f"      Content: {result.chunk.content[:150]}...")
            print()
    
except Exception as e:
    print(f"Error with semantic search: {e}")
    import traceback
    traceback.print_exc()
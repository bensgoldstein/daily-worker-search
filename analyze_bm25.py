"""Analyze BM25 search functionality without Pinecone"""

import pickle
import numpy as np
from pathlib import Path
from rank_bm25 import BM25Okapi

print("Loading BM25 data...")
bm25_path = Path("processed_data/bm25_index_hosted.pkl")

if not bm25_path.exists():
    print("BM25 index file not found!")
    exit(1)

try:
    with open(bm25_path, 'rb') as f:
        data = pickle.load(f)
    
    chunks = data['chunks']
    chunk_texts = data['chunk_texts']
    
    print(f"Loaded {len(chunks)} chunks from BM25 index")
    print(f"Date range: {min(c.newspaper_metadata.publication_date for c in chunks)} to {max(c.newspaper_metadata.publication_date for c in chunks)}")
    
    # Build BM25
    tokenized_texts = [text.lower().split() for text in chunk_texts]
    bm25 = BM25Okapi(tokenized_texts)
    
    # Test femininity-related queries
    test_queries = [
        "How did communists discuss femininity?",
        "femininity feminine",
        "woman women",
        "gender roles",
        "female workers",
        "communist women",
        "women's rights",
        "housewife domestic",
        "mother motherhood",
        "family wife"
    ]
    
    print(f"\n{'='*80}")
    print("BM25 KEYWORD SEARCH ANALYSIS")
    print(f"{'='*80}")
    
    for query_text in test_queries:
        query_tokens = query_text.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)
        
        # Get statistics
        max_score = max(bm25_scores)
        results_above_zero = sum(1 for s in bm25_scores if s > 0)
        
        # Different score thresholds to test
        score_thresholds = [0.5, 1.0, 2.0, 5.0, 10.0]
        
        print(f"\n--- Query: '{query_text}' ---")
        print(f"Max BM25 score: {max_score:.4f}")
        print(f"Results with score > 0: {results_above_zero}")
        
        for threshold in score_thresholds:
            above_threshold = sum(1 for s in bm25_scores if s >= threshold)
            print(f"Results >= {threshold}: {above_threshold}")
        
        # Show top results if any exist
        if max_score > 0:
            top_indices = np.argsort(bm25_scores)[::-1][:5]
            print("\nTop 5 matches:")
            
            for i, idx in enumerate(top_indices):
                score = bm25_scores[idx]
                if score > 0:
                    chunk = chunks[idx]
                    # Normalize BM25 score like the system does
                    normalized_score = min(score / 10.0, 1.0)
                    
                    print(f"  {i+1}. BM25 Score: {score:.4f} (normalized: {normalized_score:.4f})")
                    print(f"      Date: {chunk.newspaper_metadata.publication_date}")
                    print(f"      Newspaper: {chunk.newspaper_metadata.newspaper_name}")
                    print(f"      Content: {chunk.content[:200]}...")
                    print()
    
    # Let's also search for exact word matches in the content
    print(f"\n{'='*80}")
    print("DIRECT TEXT SEARCH IN CONTENT")
    print(f"{'='*80}")
    
    search_terms = ["femininity", "feminine", "woman", "women", "female", "gender"]
    
    for term in search_terms:
        matches = []
        for i, chunk in enumerate(chunks):
            if term.lower() in chunk.content.lower():
                matches.append((i, chunk))
        
        print(f"\n--- Direct matches for '{term}' ---")
        print(f"Found {len(matches)} chunks containing '{term}'")
        
        # Show first few matches
        for i, (idx, chunk) in enumerate(matches[:3]):
            print(f"  {i+1}. Date: {chunk.newspaper_metadata.publication_date}")
            print(f"      Newspaper: {chunk.newspaper_metadata.newspaper_name}")
            # Find the context around the term
            content_lower = chunk.content.lower()
            term_pos = content_lower.find(term.lower())
            if term_pos >= 0:
                start = max(0, term_pos - 100)
                end = min(len(chunk.content), term_pos + 100)
                context = chunk.content[start:end]
                print(f"      Context: ...{context}...")
            print()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
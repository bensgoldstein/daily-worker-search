"""Quick test of BM25 search for specific terms"""

import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi
import numpy as np

print("Loading BM25 data (this may take a moment)...")
bm25_path = Path("processed_data/bm25_index_hosted.pkl")

with open(bm25_path, 'rb') as f:
    data = pickle.load(f)

chunks = data['chunks']
chunk_texts = data['chunk_texts']

# Sample a smaller subset to test quickly
print(f"Full dataset: {len(chunks)} chunks")
sample_size = min(10000, len(chunks))  # Test with first 10k chunks
print(f"Testing with sample of {sample_size} chunks...")

sample_chunks = chunks[:sample_size]
sample_texts = chunk_texts[:sample_size]

# Build BM25 on sample
tokenized_texts = [text.lower().split() for text in sample_texts]
bm25 = BM25Okapi(tokenized_texts)

# Quick test searches
test_terms = ["femininity", "feminine", "woman", "women", "female", "gender", "wife", "mother"]

for term in test_terms:
    print(f"\n--- Testing '{term}' ---")
    
    # Direct text search first
    direct_matches = sum(1 for text in sample_texts if term.lower() in text.lower())
    print(f"Direct text matches: {direct_matches}")
    
    # BM25 search
    bm25_scores = bm25.get_scores([term.lower()])
    max_score = max(bm25_scores)
    above_zero = sum(1 for s in bm25_scores if s > 0)
    
    print(f"BM25 max score: {max_score:.4f}")
    print(f"BM25 results > 0: {above_zero}")
    
    # Show top match if exists
    if max_score > 0:
        top_idx = np.argmax(bm25_scores)
        chunk = sample_chunks[top_idx]
        print(f"Top match score: {bm25_scores[top_idx]:.4f}")
        print(f"Date: {chunk.newspaper_metadata.publication_date}")
        print(f"Content sample: {chunk.content[:150]}...")

print(f"\n--- Summary of {sample_size} chunk sample ---")
print("Dataset covers Daily Worker and The Worker newspapers from 1924-1958")
print("Total words in dataset: ~250 million")
print("If no matches found in sample, full dataset search may still find results")
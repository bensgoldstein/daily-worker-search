"""Test search functionality for femininity-related queries"""

from datetime import date
from dotenv import load_dotenv
load_dotenv()

from vector_database_hosted import VectorDatabaseHosted
from models import SearchQuery
import traceback

# Initialize
print("Initializing vector database...")
try:
    vector_db = VectorDatabaseHosted()
    
    # Load BM25 index if available
    from pathlib import Path
    bm25_path = Path("processed_data/bm25_index_hosted.pkl")
    if bm25_path.exists():
        vector_db.load_bm25_index(bm25_path)
        print("BM25 index loaded successfully")
    else:
        print("WARNING: BM25 index not found")
    
    print("Vector database initialized successfully")
except Exception as e:
    print(f"Error initializing vector database: {e}")
    traceback.print_exc()
    exit(1)

# Test queries related to femininity
test_queries = [
    "How did communists discuss femininity?",
    "femininity",
    "feminine",
    "woman",
    "women",
    "gender roles",
    "female workers",
    "communist women"
]

# Test with different relevance thresholds
thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]

for query_text in test_queries:
    print(f"\n{'='*60}")
    print(f"TESTING QUERY: '{query_text}'")
    print(f"{'='*60}")
    
    for threshold in thresholds:
        print(f"\n--- Relevance Threshold: {threshold} ---")
        
        # Create query with current threshold
        query = SearchQuery(
            query_text=query_text,
            search_type="hybrid",
            max_results=20,
            relevance_threshold=threshold,
            start_date=date(1924, 1, 1),  # Full date range
            end_date=date(1958, 12, 31)
        )
        
        try:
            results = vector_db.search(query)
            print(f"Found {len(results)} results")
            
            if results:
                print("Top 3 results:")
                for i, result in enumerate(results[:3]):
                    print(f"  {i+1}. Score: {result.relevance_score:.4f}")
                    print(f"      Date: {result.chunk.newspaper_metadata.publication_date}")
                    print(f"      Newspaper: {result.chunk.newspaper_metadata.newspaper_name}")
                    print(f"      Content: {result.chunk.content[:150]}...")
                    print()
            else:
                print("  No results found")
                
        except Exception as e:
            print(f"  Error: {e}")
            traceback.print_exc()

print(f"\n{'='*60}")
print("TESTING DIFFERENT SEARCH TYPES")
print(f"{'='*60}")

query_text = "How did communists discuss femininity?"
search_types = ["semantic", "keyword", "hybrid"]

for search_type in search_types:
    print(f"\n--- Search Type: {search_type} ---")
    
    query = SearchQuery(
        query_text=query_text,
        search_type=search_type,
        max_results=20,
        relevance_threshold=0.5,  # Lower threshold to see more results
        start_date=date(1924, 1, 1),
        end_date=date(1958, 12, 31)
    )
    
    try:
        results = vector_db.search(query)
        print(f"Found {len(results)} results")
        
        if results:
            print("Top 3 results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. Score: {result.relevance_score:.4f}")
                print(f"      Date: {result.chunk.newspaper_metadata.publication_date}")
                print(f"      Content: {result.chunk.content[:150]}...")
                print()
        else:
            print("  No results found")
            
    except Exception as e:
        print(f"  Error: {e}")
        traceback.print_exc()
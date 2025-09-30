"""Test search functionality"""

from datetime import date
from dotenv import load_dotenv
load_dotenv()

from vector_database_hosted import VectorDatabaseHosted
from models import SearchQuery

# Initialize
print("Initializing vector database...")
vector_db = VectorDatabaseHosted()

# Create a simple query without date filters
query = SearchQuery(
    query_text="labor strikes",
    search_type="semantic",
    max_results=5
)

print(f"Searching for: {query.query_text}")
print(f"Search type: {query.search_type}")
print(f"Date filters: start={query.start_date}, end={query.end_date}")

try:
    results = vector_db.search(query)
    print(f"\nFound {len(results)} results")
    
    for i, result in enumerate(results[:3]):
        print(f"\n{i+1}. Score: {result.relevance_score:.3f}")
        print(f"   Date: {result.chunk.newspaper_metadata.publication_date}")
        print(f"   Content: {result.chunk.content[:100]}...")
        
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
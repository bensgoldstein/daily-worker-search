"""Test script to verify Pinecone hosted embedding format."""

import os
from dotenv import load_dotenv
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX_NAME", "newspaper-rag")
index = pc.Index(index_name)

# Test with a single record
test_data = [{
    "id": "test-001",
    "metadata": {
        "text": "This is a test document for the Daily Worker newspaper from 1924.",
        "newspaper_name": "Daily Worker",
        "publication_date": "1924-01-05"
    }
}]

print("Testing Pinecone hosted embedding format...")
print(f"Index: {index_name}")
print(f"Test data: {test_data}")

# Check if this is an inference-enabled index
try:
    index_info = index.describe_index_stats()
    print(f"Index info: {index_info}")
except Exception as e:
    print(f"Could not get index info: {e}")

# For inference-enabled indexes, we need to embed the text first
try:
    # Method 1: Use inference API directly
    from pinecone.grpc import PineconeGRPC
    
    # Try to embed text using the inference model
    text_to_embed = "This is a test document for the Daily Worker newspaper from 1924."
    
    # For hosted embeddings, we need to call the embed endpoint
    result = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[text_to_embed],
        parameters={"input_type": "passage", "truncate": "END"}
    )
    
    print(f"Embedding successful: {len(result[0].values)} dimensions")
    
    # Now upsert with the actual embeddings
    upsert_data = [{
        "id": "test-001",
        "values": result[0].values,
        "metadata": {
            "text": text_to_embed,
            "newspaper_name": "Daily Worker", 
            "publication_date": "1924-01-05"
        }
    }]
    
    upsert_result = index.upsert(vectors=upsert_data)
    print(f"Upsert successful: {upsert_result}")
    
except Exception as e:
    print(f"Inference method failed: {e}")
    
    # Method 2: Maybe it's automatic with the right format
    try:
        auto_data = [{
            "id": "test-003",
            "values": [],  # Let Pinecone handle embedding
            "metadata": {
                "text": "This is a test document for the Daily Worker newspaper from 1924.",
                "newspaper_name": "Daily Worker",
                "publication_date": "1924-01-05"  
            }
        }]
        
        result = index.upsert(vectors=auto_data)
        print(f"Auto-embedding worked: {result}")
        
    except Exception as e2:
        print(f"Auto-embedding also failed: {e2}")
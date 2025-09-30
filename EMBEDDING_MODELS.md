# Embedding Model Options

## Current Model
- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Dimensions**: 384
- **Size**: ~80MB
- **Speed**: Very fast
- **Quality**: Good for general use

## Better Alternatives

### 1. all-mpnet-base-v2 (Recommended upgrade)
- **Dimensions**: 768
- **Size**: ~420MB
- **Speed**: Fast
- **Quality**: Best quality/speed trade-off
- **Why**: Significantly better semantic understanding

### 2. all-MiniLM-L12-v2
- **Dimensions**: 384
- **Size**: ~120MB
- **Speed**: Fast
- **Quality**: Better than L6, same dimensions

### 3. OpenAI text-embedding-ada-002
- **Dimensions**: 1536
- **Size**: N/A (API-based)
- **Speed**: Medium (API calls)
- **Quality**: Excellent
- **Cost**: $0.0001 per 1K tokens
- **Why**: State-of-the-art quality

### 4. Cohere embed-english-v3.0
- **Dimensions**: 1024
- **Size**: N/A (API-based)
- **Speed**: Fast API
- **Quality**: Excellent
- **Cost**: Free tier available

## To Change Models

1. Update `config.py`:
```python
# For all-mpnet-base-v2 (768 dims)
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
EMBEDDING_DIMENSION = 768

# For OpenAI (1536 dims)
EMBEDDING_MODEL = "openai/text-embedding-ada-002"
EMBEDDING_DIMENSION = 1536
```

2. Create Pinecone index with matching dimensions

3. Re-process and re-index your data

## Recommendation

For your use case with historical newspapers, I recommend:

1. **If staying local**: Use all-mpnet-base-v2 (768 dims)
   - 2x better than current model
   - Still runs locally
   - Good balance of quality and speed

2. **If using API**: OpenAI embeddings (1536 dims)
   - Best quality for semantic search
   - Handles historical language better
   - But adds API costs

The 384 dimensions of all-MiniLM-L6-v2 is indeed small, but it's fast and free. Upgrading to 768+ dimensions will give you noticeably better search results.
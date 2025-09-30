# Newspaper RAG Deployment Roadmap (with Pinecone)

## Big Pieces Needed for Deployment

### 1. **Pinecone Setup** ✅ LOCKED IN
- Create Pinecone account (if not already)
- Get API key
- Create index with proper dimensions (384 for all-MiniLM-L6-v2)
- Configure index settings

### 2. **Process and Index Data**
```bash
# Step 1: Process Daily Worker locally
python process_daily_worker.py \
    --input-dir "C:\Users\Benjamin\Downloads\DailyWorker-20250927T145711Z-1-001\DailyWorker" \
    --output-dir "processed_data"

# Step 2: Index to Pinecone (requires API key in .env)
# This will upload all vectors to Pinecone cloud
```

### 3. **Environment Configuration**

Create `.env` file:
```env
# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=gcp-starter
PINECONE_INDEX_NAME=newspaper-rag

# Optional: OpenAI for enhanced responses
OPENAI_API_KEY=your-openai-key

# App Configuration
LOG_LEVEL=INFO
```

### 4. **Streamlit Deployment Options**

#### Option A: Streamlit Community Cloud (Recommended)
**Pros**: Free, easy, integrated with GitHub
**Cons**: Public only, resource limits

#### Option B: Heroku
**Pros**: More control, can be private
**Cons**: Costs money, more setup

#### Option C: Railway/Render
**Pros**: Modern platforms, good free tiers
**Cons**: May have timeouts

### 5. **Deployment Preparation**

#### Create Streamlit Secrets
For Streamlit Cloud, create `.streamlit/secrets.toml`:
```toml
PINECONE_API_KEY = "your-pinecone-api-key"
PINECONE_ENVIRONMENT = "gcp-starter"
PINECONE_INDEX_NAME = "newspaper-rag"
OPENAI_API_KEY = "your-openai-key"  # Optional
```

#### Optimize Dependencies
Create `requirements_deploy.txt`:
```txt
# Core
streamlit==1.28.0
python-dotenv==1.0.0

# Vector Search
pinecone-client==2.2.4
sentence-transformers==2.2.2

# Search & Processing
rank-bm25==0.2.2
pandas==2.0.0
numpy==1.24.0

# Logging
loguru==0.7.0

# Remove heavy dependencies not needed for search-only deployment
```

### 6. **Data Indexing Strategy**

Since Pinecone stores vectors in the cloud, you need to:

1. **One-time local processing & upload**:
```python
# index_to_pinecone.py
import pickle
from vector_database import VectorDatabase

# Load processed chunks
with open('processed_data/daily_worker_chunks.pkl', 'rb') as f:
    chunks = pickle.load(f)

# Initialize Pinecone
vector_db = VectorDatabase()

# Index all chunks (this will take time)
vector_db.index_chunks(chunks, batch_size=100)
print("Indexing complete!")
```

2. **BM25 Index Storage**:
- Option A: Include BM25 index in GitHub repo (if < 100MB)
- Option B: Store in cloud storage and download on app start
- Option C: Rebuild from stored text (slower but simpler)

## Action Plan

### Phase 1: Pinecone Setup (Day 1)
1. Create Pinecone account at https://www.pinecone.io/
2. Create new index:
   - Name: `newspaper-rag`
   - Dimensions: `384`
   - Metric: `cosine`
   - Environment: `gcp-starter` (free tier)
3. Copy API key

### Phase 2: Local Processing & Indexing (Day 1-2)
```bash
# 1. Create .env file with Pinecone credentials
echo "PINECONE_API_KEY=your-key-here" > .env
echo "PINECONE_ENVIRONMENT=gcp-starter" >> .env
echo "PINECONE_INDEX_NAME=newspaper-rag" >> .env

# 2. Process Daily Worker dataset
python process_daily_worker.py \
    --input-dir "path/to/DailyWorker" \
    --output-dir "processed_data"

# 3. Upload to Pinecone (this will take 1-2 hours)
python index_to_pinecone.py
```

### Phase 3: Prepare for Deployment (Day 2)
1. Create deployment repository structure:
```
newspaper-rag-deploy/
├── app.py                    # Your Streamlit app
├── requirements.txt          # Deployment dependencies
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── config.py                # App configuration
├── models.py                # Data models
├── vector_database.py       # Pinecone interface
└── bm25_index.pkl          # Pre-built BM25 index (if small enough)
```

2. Test locally with Pinecone:
```bash
streamlit run app.py
```

### Phase 4: Deploy to Streamlit Cloud (Day 3)
1. Push to GitHub
2. Go to share.streamlit.io
3. Connect your GitHub repo
4. Add secrets (Pinecone API key)
5. Deploy!

## Key Considerations

### Costs
- **Pinecone Free Tier**: 1M vectors, should be enough for ~10-20k newspaper issues
- **Streamlit Cloud**: Free for public apps
- **Total monthly cost**: $0 (within free tiers)

### Performance
- First query might be slow (loading models)
- Subsequent queries should be fast (~1-2 seconds)
- Consider caching strategies for common queries

### Data Updates
To add new newspapers:
1. Process locally
2. Upload new vectors to Pinecone
3. Update BM25 index
4. Redeploy app

## Next Steps

1. **Get Pinecone API key** (5 minutes)
2. **Run full Daily Worker processing** (10 minutes)
3. **Upload to Pinecone** (1-2 hours)
4. **Test app locally** (30 minutes)
5. **Deploy to Streamlit Cloud** (30 minutes)

Total time to deployment: ~3-4 hours of active work

The app will then be live at: `https://[your-app-name].streamlit.app`
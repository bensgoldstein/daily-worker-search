# Newspaper RAG - Historical Newspaper Search System

A Retrieval-Augmented Generation (RAG) system for searching historical newspapers from Internet Archive. This system provides date-based filtering and online hosting capabilities.

## Features

- **OCR Text Processing**: Processes OCR-extracted text from Internet Archive newspapers
- **Date-based Filtering**: Filter search results by newspaper publication date
- **Online Hosting**: Fully hosted online with Streamlit interface
- **Hybrid Search**: Combines semantic search with BM25 for optimal retrieval
- **Metadata Preservation**: Maintains newspaper date and source information

## Architecture

### Data Processing Pipeline
1. **Local Processing**: 
   - Extract OCR text from Internet Archive newspapers
   - Parse metadata including publication dates
   - Chunk documents with overlap for better context
   - Generate embeddings using sentence-transformers

2. **Online Storage**:
   - Vector embeddings stored in Pinecone/Weaviate cloud
   - Document metadata and text stored in cloud database
   - BM25 index stored for hybrid search

3. **Web Interface**:
   - Streamlit application for search interface
   - Date range filtering
   - Source attribution for all results

## Setup

### Prerequisites
- Python 3.8+
- Internet Archive newspaper files (txt format with metadata)
- Cloud vector database account (Pinecone/Weaviate)
- Streamlit Cloud account for deployment

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
Set environment variables in `.env`:
```
VECTOR_DB_API_KEY=your_api_key
VECTOR_DB_ENVIRONMENT=your_environment
OPENAI_API_KEY=your_openai_key  # For response generation
```

## Usage

### Data Processing
```bash
python process_newspapers.py --input-dir /path/to/newspapers --output-dir /path/to/processed
```

### Running Locally
```bash
streamlit run app.py
```

### Deployment
Deploy to Streamlit Cloud using the provided configuration.
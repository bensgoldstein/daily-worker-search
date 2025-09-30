"""Script to index processed newspaper chunks to Pinecone."""

import pickle
import sys
from pathlib import Path
import time
from loguru import logger
import argparse

from vector_database import VectorDatabase
from config import config


def setup_logging():
    """Setup logging configuration."""
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    )
    
    logger.add(
        "pinecone_indexing.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB"
    )


def main():
    parser = argparse.ArgumentParser(description="Index processed chunks to Pinecone")
    parser.add_argument(
        "--chunks-file",
        type=str,
        default="processed_data/daily_worker_chunks.pkl",
        help="Path to processed chunks pickle file"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for indexing (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without indexing"
    )
    
    args = parser.parse_args()
    
    setup_logging()
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please ensure your .env file contains PINECONE_API_KEY")
        sys.exit(1)
    
    # Load chunks
    chunks_path = Path(args.chunks_file)
    if not chunks_path.exists():
        logger.error(f"Chunks file not found: {chunks_path}")
        logger.error("Please run process_daily_worker.py first to create chunks")
        sys.exit(1)
    
    logger.info(f"Loading chunks from {chunks_path}")
    with open(chunks_path, 'rb') as f:
        chunks = pickle.load(f)
    
    logger.info(f"Loaded {len(chunks)} chunks")
    
    if args.dry_run:
        logger.info("DRY RUN - Summary of chunks to index:")
        logger.info(f"Total chunks: {len(chunks)}")
        
        # Sample first few chunks
        for i, chunk in enumerate(chunks[:3]):
            logger.info(f"\nSample chunk {i+1}:")
            logger.info(f"  Date: {chunk.newspaper_metadata.publication_date}")
            logger.info(f"  Newspaper: {chunk.newspaper_metadata.newspaper_name}")
            logger.info(f"  Content preview: {chunk.content[:100]}...")
        
        logger.info("\nDry run complete. Add --no-dry-run to actually index.")
        return
    
    # Initialize vector database
    logger.info("Initializing Pinecone connection...")
    try:
        vector_db = VectorDatabase()
        logger.info(f"Connected to Pinecone index: {config.PINECONE_INDEX_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to Pinecone: {e}")
        sys.exit(1)
    
    # Start indexing
    logger.info("=" * 60)
    logger.info("Starting indexing to Pinecone")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # Index chunks
        vector_db.index_chunks(chunks, batch_size=args.batch_size)
        
        # Save BM25 index locally
        bm25_path = chunks_path.parent / "bm25_index.pkl"
        vector_db.save_bm25_index(bm25_path)
        logger.info(f"Saved BM25 index to {bm25_path}")
        
    except Exception as e:
        logger.error(f"Error during indexing: {e}")
        sys.exit(1)
    
    elapsed_time = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info("Indexing Complete!")
    logger.info(f"Total chunks indexed: {len(chunks)}")
    logger.info(f"Time taken: {elapsed_time:.2f} seconds")
    logger.info(f"Average time per chunk: {elapsed_time/len(chunks):.3f} seconds")
    logger.info("=" * 60)
    
    logger.info("\nYour newspaper data is now indexed in Pinecone!")
    logger.info("You can now run the Streamlit app to search the data.")


if __name__ == "__main__":
    main()
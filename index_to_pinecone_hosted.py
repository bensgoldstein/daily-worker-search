"""Script to index newspaper chunks to Pinecone with hosted embeddings."""

import pickle
import sys
from pathlib import Path
import time
from loguru import logger
import argparse

from vector_database_hosted import VectorDatabaseHosted
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
        "pinecone_hosted_indexing.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB"
    )


def main():
    parser = argparse.ArgumentParser(description="Index processed chunks to Pinecone with hosted embeddings")
    parser.add_argument(
        "--chunks-file",
        type=str,
        default="processed_data/daily_worker_chunks.pkl",
        help="Path to processed chunks pickle file"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for indexing (default: 50, max 96 for multilingual-e5-large)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without indexing"
    )
    
    args = parser.parse_args()
    
    setup_logging()
    
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
        
        # Calculate approximate upload size
        total_chars = sum(len(chunk.content) for chunk in chunks)
        logger.info(f"Total text size: {total_chars:,} characters (~{total_chars/1000000:.1f} MB)")
        
        # Sample first few chunks
        for i, chunk in enumerate(chunks[:3]):
            logger.info(f"\nSample chunk {i+1}:")
            logger.info(f"  Date: {chunk.newspaper_metadata.publication_date}")
            logger.info(f"  Newspaper: {chunk.newspaper_metadata.newspaper_name}")
            logger.info(f"  Length: {len(chunk.content)} chars")
            logger.info(f"  Content preview: {chunk.content[:100]}...")
        
        logger.info("\nDry run complete. Remove --dry-run to actually index.")
        return
    
    # Initialize vector database
    logger.info("Initializing Pinecone connection...")
    try:
        vector_db = VectorDatabaseHosted()
        logger.info(f"Connected to Pinecone index: {config.PINECONE_INDEX_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to Pinecone: {e}")
        sys.exit(1)
    
    # Start indexing
    logger.info("=" * 60)
    logger.info("Starting indexing to Pinecone with hosted embeddings")
    logger.info(f"Using model: multilingual-e5-large")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # Index chunks
        vector_db.index_chunks(chunks, batch_size=args.batch_size)
        
        # Save BM25 index locally for hybrid search
        bm25_path = chunks_path.parent / "bm25_index_hosted.pkl"
        vector_db.save_bm25_index(bm25_path)
        logger.info(f"Saved BM25 index to {bm25_path}")
        
    except Exception as e:
        logger.error(f"Error during indexing: {e}")
        sys.exit(1)
    
    elapsed_time = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info("Indexing Complete!")
    logger.info(f"Total chunks indexed: {len(chunks)}")
    logger.info(f"Time taken: {elapsed_time:.2f} seconds ({elapsed_time/60:.1f} minutes)")
    logger.info(f"Average time per chunk: {elapsed_time/len(chunks):.3f} seconds")
    logger.info("=" * 60)
    
    logger.info("\nYour newspaper data is now indexed in Pinecone!")
    logger.info("The multilingual-e5-large model created embeddings automatically.")
    logger.info("You can now run the Streamlit app to search the data.")


if __name__ == "__main__":
    main()
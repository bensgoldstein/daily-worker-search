"""Resume indexing from where it left off."""

import pickle
import sys
from pathlib import Path
import time
from loguru import logger
import argparse
from dotenv import load_dotenv
import os

from vector_database_hosted import VectorDatabaseHosted
from config import config

# Load environment variables
load_dotenv()


def setup_logging():
    """Setup logging configuration."""
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    )
    
    logger.add(
        "pinecone_resume_indexing.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB"
    )


def check_existing_vectors(vector_db, chunks):
    """Check which chunks are already indexed."""
    logger.info("Checking existing vectors in Pinecone...")
    
    # Get index stats
    stats = vector_db.index.describe_index_stats()
    logger.info(f"Current vectors in index: {stats['total_vector_count']}")
    
    # Get a sample of existing IDs to verify
    existing_ids = set()
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    
    # Check in batches
    batch_size = 1000
    logger.info(f"Checking which of our {len(chunks)} chunks are already indexed...")
    
    for i in range(0, len(chunk_ids), batch_size):
        batch_ids = chunk_ids[i:i + batch_size]
        try:
            # Fetch vectors by IDs
            response = vector_db.index.fetch(ids=batch_ids)
            
            # Handle new API response format
            if hasattr(response, 'vectors'):
                existing_ids.update(response.vectors.keys())
            else:
                # Try dict access
                existing_ids.update(response.get('vectors', {}).keys())
            
            if i % 10000 == 0:
                logger.info(f"Checked {i} chunks, found {len(existing_ids)} already indexed")
        except Exception as e:
            logger.warning(f"Error checking batch {i//batch_size}: {e}")
    
    logger.info(f"Total existing chunks found: {len(existing_ids)}")
    
    # Filter out already indexed chunks
    remaining_chunks = [chunk for chunk in chunks if chunk.chunk_id not in existing_ids]
    logger.info(f"Remaining chunks to index: {len(remaining_chunks)}")
    
    return remaining_chunks, len(existing_ids)


def main():
    parser = argparse.ArgumentParser(description="Resume indexing to Pinecone")
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
        "--check-only",
        action="store_true",
        help="Only check what's indexed, don't resume"
    )
    
    args = parser.parse_args()
    
    setup_logging()
    
    # Load chunks
    chunks_path = Path(args.chunks_file)
    logger.info(f"Loading chunks from {chunks_path}")
    with open(chunks_path, 'rb') as f:
        chunks = pickle.load(f)
    
    logger.info(f"Loaded {len(chunks)} total chunks")
    
    # Initialize vector database
    logger.info("Initializing Pinecone connection...")
    try:
        vector_db = VectorDatabaseHosted()
        logger.info(f"Connected to Pinecone index: {config.PINECONE_INDEX_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to Pinecone: {e}")
        sys.exit(1)
    
    # Check what's already indexed
    remaining_chunks, already_indexed = check_existing_vectors(vector_db, chunks)
    
    completion_percentage = (already_indexed / len(chunks)) * 100
    logger.info(f"Progress: {already_indexed}/{len(chunks)} chunks ({completion_percentage:.1f}% complete)")
    
    if args.check_only:
        logger.info("Check-only mode. Exiting.")
        return
    
    if not remaining_chunks:
        logger.info("All chunks are already indexed! Nothing to do.")
        return
    
    # Resume indexing
    logger.info("=" * 60)
    logger.info("Resuming indexing to Pinecone")
    logger.info(f"Chunks to process: {len(remaining_chunks)}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # Use the same indexing method but with remaining chunks only
        vector_db.chunks = chunks  # Need full list for BM25
        vector_db.chunk_texts = [chunk.content for chunk in chunks]
        
        # Index only remaining chunks
        vector_db.index_chunks(remaining_chunks, batch_size=args.batch_size)
        
        # Save updated BM25 index
        bm25_path = chunks_path.parent / "bm25_index_hosted.pkl"
        vector_db.save_bm25_index(bm25_path)
        logger.info(f"Updated BM25 index saved to {bm25_path}")
        
    except Exception as e:
        logger.error(f"Error during indexing: {e}")
        logger.info(f"Successfully indexed up to this point. You can resume again later.")
        sys.exit(1)
    
    elapsed_time = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info("Indexing Complete!")
    logger.info(f"Additional chunks indexed: {len(remaining_chunks)}")
    logger.info(f"Total chunks now indexed: {len(chunks)}")
    logger.info(f"Time taken: {elapsed_time:.2f} seconds ({elapsed_time/60:.1f} minutes)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
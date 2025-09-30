"""Resume indexing from where it left off - simplified version."""

import pickle
import sys
from pathlib import Path
import time
from loguru import logger
import argparse
from dotenv import load_dotenv

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
        help="Batch size for indexing (default: 50)"
    )
    parser.add_argument(
        "--skip-first",
        type=int,
        default=None,
        help="Number of chunks to skip (will auto-detect if not provided)"
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
    
    # Get current index stats
    stats = vector_db.index.describe_index_stats()
    already_indexed = stats['total_vector_count']
    logger.info(f"Current vectors in index: {already_indexed}")
    
    # Determine how many to skip
    skip_count = args.skip_first if args.skip_first is not None else already_indexed
    
    # Safety check - we uploaded in batches of 50, so round down to nearest 50
    skip_count = (skip_count // 50) * 50
    logger.info(f"Skipping first {skip_count} chunks (already indexed)")
    
    # Get remaining chunks
    remaining_chunks = chunks[skip_count:]
    
    if not remaining_chunks:
        logger.info("All chunks appear to be indexed! Nothing to do.")
        return
    
    completion_percentage = (skip_count / len(chunks)) * 100
    logger.info(f"Progress: {skip_count}/{len(chunks)} chunks ({completion_percentage:.1f}% complete)")
    logger.info(f"Remaining chunks to index: {len(remaining_chunks)}")
    
    # Estimate time
    if skip_count > 0:
        # Estimate based on previous rate (55100 chunks in ~50 minutes)
        rate = 55100 / (50 * 60)  # chunks per second
        estimated_time = len(remaining_chunks) / rate / 3600  # hours
        logger.info(f"Estimated time remaining: {estimated_time:.1f} hours")
    
    # Resume indexing
    logger.info("=" * 60)
    logger.info("Resuming indexing to Pinecone")
    logger.info(f"Starting from chunk #{skip_count}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 60)
    
    # Confirm before proceeding
    response = input("\nProceed with indexing? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("Cancelled by user")
        return
    
    start_time = time.time()
    
    try:
        # We need to pass all chunks for BM25, but only index the remaining ones
        vector_db.chunks = chunks
        vector_db.chunk_texts = [chunk.content for chunk in chunks]
        
        # Index only remaining chunks
        vector_db.index_chunks(remaining_chunks, batch_size=args.batch_size)
        
        # Save updated BM25 index
        bm25_path = chunks_path.parent / "bm25_index_hosted.pkl"
        vector_db.save_bm25_index(bm25_path)
        logger.info(f"Updated BM25 index saved to {bm25_path}")
        
    except Exception as e:
        logger.error(f"Error during indexing: {e}")
        
        # Show progress
        final_stats = vector_db.index.describe_index_stats()
        final_count = final_stats['total_vector_count']
        newly_indexed = final_count - already_indexed
        
        logger.info(f"Successfully indexed {newly_indexed} additional chunks before error")
        logger.info(f"Total now in index: {final_count}")
        logger.info("You can resume again by running this script")
        sys.exit(1)
    
    elapsed_time = time.time() - start_time
    
    # Final stats
    final_stats = vector_db.index.describe_index_stats()
    final_count = final_stats['total_vector_count']
    newly_indexed = final_count - already_indexed
    
    logger.info("=" * 60)
    logger.info("Indexing Complete!")
    logger.info(f"Newly indexed chunks: {newly_indexed}")
    logger.info(f"Total chunks now indexed: {final_count}")
    logger.info(f"Time taken: {elapsed_time:.2f} seconds ({elapsed_time/60:.1f} minutes)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
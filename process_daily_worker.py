"""Batch processing script specifically for Daily Worker newspaper files."""

import argparse
import sys
from pathlib import Path
import time
from datetime import datetime
import pickle
from loguru import logger

from daily_worker_processor import DailyWorkerProcessor
from vector_database import VectorDatabase
from config import config


def setup_logging(log_dir: Path):
    """Setup logging configuration."""
    log_dir.mkdir(exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stdout,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    )
    
    # File logging
    log_file = log_dir / f"daily_worker_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB"
    )
    
    logger.info(f"Logging to {log_file}")


def main():
    parser = argparse.ArgumentParser(description="Process Daily Worker newspaper OCR files for RAG system")
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing Daily Worker files (e.g., DailyWorker folder)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save processed data"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=config.CHUNK_SIZE,
        help=f"Chunk size in words (default: {config.CHUNK_SIZE})"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=config.CHUNK_OVERLAP,
        help=f"Chunk overlap in words (default: {config.CHUNK_OVERLAP})"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=config.BATCH_SIZE,
        help=f"Batch size for indexing (default: {config.BATCH_SIZE})"
    )
    parser.add_argument(
        "--skip-indexing",
        action="store_true",
        help="Skip vector database indexing (only process and save chunks)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without processing"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit processing to first N files (useful for testing)"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_dir = output_dir / "logs"
    setup_logging(log_dir)
    
    logger.info("=" * 60)
    logger.info(f"Daily Worker Processing Started")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Chunk size: {args.chunk_size} words")
    logger.info(f"Chunk overlap: {args.chunk_overlap} words")
    if args.limit:
        logger.info(f"Processing limit: {args.limit} files")
    logger.info("=" * 60)
    
    if args.dry_run:
        # Just count files
        files = list(input_dir.rglob("per_daily-worker_*_djvu.txt"))
        logger.info(f"DRY RUN: Found {len(files)} Daily Worker files")
        
        # Show date range
        if files:
            # Extract dates from directory names
            dates = []
            for file in files:
                match = re.match(r'^per_daily-worker_(\d{4}-\d{2}-\d{2})_', file.parent.name)
                if match:
                    dates.append(match.group(1))
            
            if dates:
                dates.sort()
                logger.info(f"Date range: {dates[0]} to {dates[-1]}")
        
        # Show sample files
        for i, file in enumerate(files[:10]):
            logger.info(f"  {i+1}. {file.parent.name}/{file.name}")
        if len(files) > 10:
            logger.info(f"  ... and {len(files) - 10} more files")
        return
    
    # Initialize processor
    processor = DailyWorkerProcessor(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    # Start processing timer
    start_time = time.time()
    
    # Process files
    logger.info("Starting document processing...")
    
    if args.limit:
        # Process with limit
        all_files = list(input_dir.rglob("per_daily-worker_*_djvu.txt"))[:args.limit]
        chunks = []
        for file in all_files:
            chunks.extend(processor.process_file(file))
    else:
        # Process all files
        chunks = processor.process_directory(input_dir)
    
    # Save chunks to file
    chunks_file = output_dir / "daily_worker_chunks.pkl"
    logger.info(f"Saving {len(chunks)} chunks to {chunks_file}")
    with open(chunks_file, 'wb') as f:
        pickle.dump(chunks, f)
    
    # Save processing stats
    stats_file = output_dir / "daily_worker_stats.json"
    processor.stats.processing_time_seconds = time.time() - start_time
    processor.save_processing_stats(stats_file)
    
    # Index in vector database if requested
    if not args.skip_indexing and chunks:
        logger.info("Initializing vector database...")
        
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            logger.info("Skipping vector indexing. Please check your .env file.")
            return
        
        vector_db = VectorDatabase()
        
        logger.info("Starting vector indexing...")
        vector_db.index_chunks(chunks, batch_size=args.batch_size)
        
        # Save BM25 index
        bm25_file = output_dir / "daily_worker_bm25_index.pkl"
        vector_db.save_bm25_index(bm25_file)
        logger.info(f"Saved BM25 index to {bm25_file}")
    
    # Final summary
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Daily Worker Processing Complete!")
    logger.info(f"Total files: {processor.stats.total_files}")
    logger.info(f"Processed files: {processor.stats.processed_files}")
    logger.info(f"Failed files: {processor.stats.failed_files}")
    logger.info(f"Total chunks: {processor.stats.total_chunks}")
    logger.info(f"Total words: {processor.stats.total_words:,}")
    
    if processor.stats.date_range:
        start_date, end_date = processor.stats.date_range
        logger.info(f"Date range: {start_date} to {end_date}")
    
    logger.info(f"Processing time: {elapsed_time:.2f} seconds")
    logger.info(f"Average time per file: {elapsed_time/processor.stats.processed_files:.2f} seconds")
    logger.info("=" * 60)


if __name__ == "__main__":
    import re  # Add this import for dry run date extraction
    main()
"""Batch processing script for newspaper OCR files."""

import argparse
import sys
from pathlib import Path
import time
from datetime import datetime
import pickle
from loguru import logger

from document_processor import NewspaperProcessor
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
    log_file = log_dir / f"processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB"
    )
    
    logger.info(f"Logging to {log_file}")


def main():
    parser = argparse.ArgumentParser(description="Process newspaper OCR files for RAG system")
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing newspaper OCR text files"
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
        "--file-pattern",
        type=str,
        default="*.txt",
        help="File pattern to match (default: *.txt)"
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
    logger.info(f"Newspaper Processing Started")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Chunk size: {args.chunk_size} words")
    logger.info(f"Chunk overlap: {args.chunk_overlap} words")
    logger.info("=" * 60)
    
    if args.dry_run:
        # Just count files
        files = list(input_dir.glob(args.file_pattern))
        logger.info(f"DRY RUN: Found {len(files)} files matching pattern '{args.file_pattern}'")
        for i, file in enumerate(files[:10]):
            logger.info(f"  {i+1}. {file.name}")
        if len(files) > 10:
            logger.info(f"  ... and {len(files) - 10} more files")
        return
    
    # Initialize processor
    processor = NewspaperProcessor(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    # Start processing timer
    start_time = time.time()
    
    # Process files
    logger.info("Starting document processing...")
    chunks = processor.process_directory(input_dir, args.file_pattern)
    
    # Save chunks to file
    chunks_file = output_dir / "processed_chunks.pkl"
    logger.info(f"Saving {len(chunks)} chunks to {chunks_file}")
    with open(chunks_file, 'wb') as f:
        pickle.dump(chunks, f)
    
    # Save processing stats
    stats_file = output_dir / "processing_stats.json"
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
        bm25_file = output_dir / "bm25_index.pkl"
        vector_db.save_bm25_index(bm25_file)
        logger.info(f"Saved BM25 index to {bm25_file}")
    
    # Final summary
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Processing Complete!")
    logger.info(f"Total files: {processor.stats.total_files}")
    logger.info(f"Processed files: {processor.stats.processed_files}")
    logger.info(f"Failed files: {processor.stats.failed_files}")
    logger.info(f"Total chunks: {processor.stats.total_chunks}")
    logger.info(f"Total words: {processor.stats.total_words:,}")
    
    if processor.stats.date_range:
        start_date, end_date = processor.stats.date_range
        logger.info(f"Date range: {start_date} to {end_date}")
    
    if processor.stats.newspapers:
        logger.info(f"Newspapers: {', '.join(processor.stats.newspapers[:5])}")
        if len(processor.stats.newspapers) > 5:
            logger.info(f"  ... and {len(processor.stats.newspapers) - 5} more")
    
    logger.info(f"Processing time: {elapsed_time:.2f} seconds")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
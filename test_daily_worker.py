"""Test script for Daily Worker processing without vector database dependencies."""

import sys
from pathlib import Path
from loguru import logger

from daily_worker_processor import DailyWorkerProcessor

# Setup simple console logging
logger.remove()
logger.add(sys.stdout, level="INFO")

def test_daily_worker_processing():
    """Test Daily Worker processing on a few sample files."""
    
    # Input directory
    input_dir = Path(r"C:\Users\Benjamin\Downloads\DailyWorker-20250927T145711Z-1-001\DailyWorker")
    
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return
    
    # Initialize processor
    processor = DailyWorkerProcessor(chunk_size=500, chunk_overlap=100)
    
    # Get sample files
    files = list(input_dir.rglob("per_daily-worker_*_djvu.txt"))[:5]
    
    logger.info(f"Found {len(files)} sample files to test")
    
    for file in files:
        logger.info(f"\nProcessing: {file.parent.name}/{file.name}")
        chunks = processor.process_file(file)
        
        if chunks:
            logger.info(f"  Created {len(chunks)} chunks")
            logger.info(f"  Metadata: {chunks[0].newspaper_metadata}")
            logger.info(f"  First chunk preview: {chunks[0].content[:200]}...")
        else:
            logger.warning(f"  No chunks created")
    
    # Print stats
    logger.info("\n" + "="*60)
    logger.info("Processing Statistics:")
    logger.info(f"Total files: {processor.stats.total_files}")
    logger.info(f"Processed files: {processor.stats.processed_files}")
    logger.info(f"Failed files: {processor.stats.failed_files}")
    logger.info(f"Total chunks: {processor.stats.total_chunks}")
    logger.info(f"Total words: {processor.stats.total_words:,}")
    
    if processor.stats.date_range:
        start_date, end_date = processor.stats.date_range
        logger.info(f"Date range: {start_date} to {end_date}")


if __name__ == "__main__":
    test_daily_worker_processing()
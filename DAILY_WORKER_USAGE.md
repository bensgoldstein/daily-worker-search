# Daily Worker Dataset Integration Guide

## Overview
The Daily Worker processor has been successfully integrated into your newspaper RAG system. The dataset contains ~9,906 issues from 1924 onwards.

## File Structure
The Daily Worker files follow this structure:
```
DailyWorker/
├── per_daily-worker_1924-01-05_6_309/
│   └── per_daily-worker_1924-01-05_6_309_djvu.txt
├── per_daily-worker_1924-01-12_6_310/
│   └── per_daily-worker_1924-01-12_6_310_djvu.txt
└── ...
```

Where:
- Directory name: `per_daily-worker_YYYY-MM-DD_VOLUME_ISSUE`
- File name: `per_daily-worker_YYYY-MM-DD_VOLUME_ISSUE_djvu.txt`

## Processing Commands

### 1. Test Processing (5 files)
```bash
python test_daily_worker.py
```

### 2. Dry Run (check dataset without processing)
```bash
python process_daily_worker.py \
    --input-dir "C:\Users\Benjamin\Downloads\DailyWorker-20250927T145711Z-1-001\DailyWorker" \
    --output-dir "C:\Users\Benjamin\.local\bin\newspaper-rag\daily_worker_output" \
    --dry-run
```

### 3. Process Limited Files (for testing)
```bash
python process_daily_worker.py \
    --input-dir "C:\Users\Benjamin\Downloads\DailyWorker-20250927T145711Z-1-001\DailyWorker" \
    --output-dir "C:\Users\Benjamin\.local\bin\newspaper-rag\daily_worker_output" \
    --limit 100 \
    --skip-indexing
```

### 4. Full Processing (without vector indexing)
```bash
python process_daily_worker.py \
    --input-dir "C:\Users\Benjamin\Downloads\DailyWorker-20250927T145711Z-1-001\DailyWorker" \
    --output-dir "C:\Users\Benjamin\.local\bin\newspaper-rag\daily_worker_output" \
    --skip-indexing
```

### 5. Full Processing with Vector Indexing (requires dependencies)
```bash
# First install dependencies
pip install -r requirements.txt

# Then run with indexing
python process_daily_worker.py \
    --input-dir "C:\Users\Benjamin\Downloads\DailyWorker-20250927T145711Z-1-001\DailyWorker" \
    --output-dir "C:\Users\Benjamin\.local\bin\newspaper-rag\daily_worker_output"
```

## Processing Options

- `--chunk-size`: Number of words per chunk (default: from config)
- `--chunk-overlap`: Number of overlapping words between chunks (default: from config)
- `--batch-size`: Batch size for vector indexing (default: from config)
- `--skip-indexing`: Skip vector database indexing (just create chunks)
- `--limit`: Process only first N files (useful for testing)
- `--dry-run`: Preview files without processing

## Output Files

After processing, you'll find:
```
daily_worker_output/
├── logs/
│   └── daily_worker_processing_YYYYMMDD_HHMMSS.log
├── daily_worker_chunks.pkl      # Processed text chunks
├── daily_worker_stats.json      # Processing statistics
└── daily_worker_bm25_index.pkl  # BM25 search index (if indexing enabled)
```

## Metadata Extracted

Each processed chunk includes:
- **Newspaper Name**: "Daily Worker"
- **Publication Date**: Extracted from directory name
- **Volume & Issue**: Extracted from directory name
- **Chunk Index**: Position within the document
- **Text Content**: OCR text (basic cleaning applied)

## Performance Estimates

Based on test results:
- ~70 chunks per issue (with 500-word chunks)
- ~28,000 words per issue
- Processing speed: ~0.04 seconds per file
- Total estimated processing time for 9,906 files: ~6-7 minutes

## Next Steps

1. Process the full dataset
2. Configure vector database credentials if needed
3. Integrate with your existing RAG query system
4. Consider adding OCR correction in post-processing if quality issues arise
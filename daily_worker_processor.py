"""Specialized processor for Daily Worker newspaper files."""

import re
from pathlib import Path
from datetime import date
from typing import Optional, List
from loguru import logger

from document_processor import NewspaperProcessor
from models import NewspaperMetadata, DocumentChunk


class DailyWorkerProcessor(NewspaperProcessor):
    """Process Daily Worker newspaper OCR text files with nested directory structure."""
    
    def extract_metadata_from_daily_worker(self, filepath: Path) -> Optional[NewspaperMetadata]:
        """
        Extract metadata from Daily Worker file path.
        Handles multiple naming patterns in the dataset.
        """
        try:
            # Get the parent directory name
            parent_dir = filepath.parent.name
            
            # Pattern 1: per_daily-worker_YYYY-MM-DD_VOLUME_ISSUE
            match = re.match(r'^per_daily-worker_(\d{4}-\d{2}-\d{2})_(\d+)_(\d+)$', parent_dir)
            if match:
                pub_date = date.fromisoformat(match.group(1))
                volume = int(match.group(2))
                issue = int(match.group(3))
                
                return NewspaperMetadata(
                    newspaper_name="Daily Worker",
                    publication_date=pub_date,
                    page_number=None,
                    section=f"Volume {volume}, Issue {issue}",
                    source_url=f"https://archive.org/details/{parent_dir}",
                    ocr_quality_score=None,
                    language='en'
                )
            
            # Pattern 2: per_daily-worker_the-worker_YYYY-MM-DD_VOLUME_ISSUE
            match = re.match(r'^per_daily-worker_the-worker_(\d{4}-\d{2}-\d{2})_(\d+)_(\d+)$', parent_dir)
            if match:
                pub_date = date.fromisoformat(match.group(1))
                volume = int(match.group(2))
                issue = int(match.group(3))
                
                return NewspaperMetadata(
                    newspaper_name="The Worker",
                    publication_date=pub_date,
                    page_number=None,
                    section=f"Volume {volume}, Issue {issue}",
                    source_url=f"https://archive.org/details/{parent_dir}",
                    ocr_quality_score=None,
                    language='en'
                )
            
            # Pattern 3: per_daily-worker_daily-worker_YYYY-MM-DD_VOLUME_ISSUE
            match = re.match(r'^per_daily-worker_daily-worker_(\d{4}-\d{2}-\d{2})_(\d+)_(\d+)$', parent_dir)
            if match:
                pub_date = date.fromisoformat(match.group(1))
                volume = int(match.group(2))
                issue = int(match.group(3))
                
                return NewspaperMetadata(
                    newspaper_name="Daily Worker",
                    publication_date=pub_date,
                    page_number=None,
                    section=f"Volume {volume}, Issue {issue}",
                    source_url=f"https://archive.org/details/{parent_dir}",
                    ocr_quality_score=None,
                    language='en'
                )
            
            # Pattern 4: Generic fallback - try to extract date at least
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', parent_dir)
            if date_match:
                pub_date = date.fromisoformat(date_match.group(1))
                
                # Determine newspaper name from directory
                if 'the-worker' in parent_dir:
                    newspaper_name = "The Worker"
                elif 'daily-worker' in parent_dir:
                    newspaper_name = "Daily Worker"
                else:
                    newspaper_name = "Daily Worker"
                
                return NewspaperMetadata(
                    newspaper_name=newspaper_name,
                    publication_date=pub_date,
                    page_number=None,
                    section="Unknown",
                    source_url=f"https://archive.org/details/{parent_dir}",
                    ocr_quality_score=None,
                    language='en'
                )
            
            logger.warning(f"Could not parse Daily Worker metadata from: {parent_dir}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Daily Worker metadata from {filepath}: {e}")
            return None
    
    def process_file(self, filepath: Path) -> List[DocumentChunk]:
        """Process a single Daily Worker file."""
        try:
            # Use specialized Daily Worker metadata extraction
            metadata = self.extract_metadata_from_daily_worker(filepath)
            if not metadata:
                logger.warning(f"Skipping file without metadata: {filepath}")
                self.stats.failed_files += 1
                return []
            
            # Read and clean text (using base class cleaning)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            cleaned_text = self.clean_ocr_text(text)
            
            if not cleaned_text:
                logger.warning(f"No text content in file: {filepath}")
                self.stats.failed_files += 1
                return []
            
            # Create chunks
            chunks = self.chunk_text(cleaned_text, metadata)
            
            # Update stats
            self.stats.processed_files += 1
            self.stats.total_chunks += len(chunks)
            self.stats.total_words += len(cleaned_text.split())
            
            # Update date range
            if self.stats.date_range:
                min_date, max_date = self.stats.date_range
                self.stats.date_range = (
                    min(min_date, metadata.publication_date),
                    max(max_date, metadata.publication_date)
                )
            else:
                self.stats.date_range = (metadata.publication_date, metadata.publication_date)
            
            # Track newspapers
            if metadata.newspaper_name not in self.stats.newspapers:
                self.stats.newspapers.append(metadata.newspaper_name)
            
            logger.info(f"Processed {filepath.name}: {len(chunks)} chunks, "
                       f"Date: {metadata.publication_date}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            self.stats.failed_files += 1
            return []
    
    def process_directory(
        self,
        directory: Path,
        file_pattern: str = "**/per_daily-worker_*_djvu.txt"
    ) -> List[DocumentChunk]:
        """
        Process all Daily Worker files in a directory with nested structure.
        Uses glob pattern to find files in subdirectories.
        """
        all_chunks = []
        
        # Get all Daily Worker text files recursively
        files = list(directory.rglob("per_daily-worker_*_djvu.txt"))
        self.stats.total_files = len(files)
        
        logger.info(f"Found {len(files)} Daily Worker files to process")
        
        # Sort files by date for consistent processing
        files.sort(key=lambda f: f.parent.name)
        
        # Process each file
        for i, filepath in enumerate(files):
            if i % 100 == 0:
                logger.info(f"Processing file {i+1}/{len(files)}: {filepath.name}")
            
            chunks = self.process_file(filepath)
            all_chunks.extend(chunks)
        
        # Sort newspapers list
        self.stats.newspapers.sort()
        
        logger.info(f"Processing complete: {self.stats.processed_files} files, "
                   f"{self.stats.total_chunks} chunks, {self.stats.failed_files} failures")
        
        return all_chunks
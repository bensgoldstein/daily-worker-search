"""Document processor for newspaper OCR text files."""

import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import json

from models import NewspaperMetadata, DocumentChunk, ProcessingStats
from config import config


class NewspaperProcessor:
    """Process newspaper OCR text files."""
    
    def __init__(
        self,
        chunk_size: int = config.CHUNK_SIZE,
        chunk_overlap: int = config.CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.stats = ProcessingStats()
        
    def extract_metadata_from_filename(self, filepath: Path) -> Optional[NewspaperMetadata]:
        """
        Extract metadata from filename and file.
        Expected format: newspaper_name_YYYY-MM-DD_page.txt
        or with metadata file: filename.txt + filename.json
        """
        try:
            # Check for accompanying metadata file
            metadata_file = filepath.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    return NewspaperMetadata(
                        newspaper_name=metadata.get('newspaper_name', 'Unknown'),
                        publication_date=date.fromisoformat(metadata['publication_date']),
                        page_number=metadata.get('page_number'),
                        section=metadata.get('section'),
                        source_url=metadata.get('source_url'),
                        ocr_quality_score=metadata.get('ocr_quality_score'),
                        language=metadata.get('language', 'en')
                    )
            
            # Try to parse from filename
            filename = filepath.stem
            
            # Pattern: newspaper_name_YYYY-MM-DD_page
            match = re.match(r'^(.+?)_(\d{4}-\d{2}-\d{2})(?:_p?(\d+))?$', filename)
            if match:
                newspaper_name = match.group(1).replace('_', ' ')
                pub_date = date.fromisoformat(match.group(2))
                page_num = int(match.group(3)) if match.group(3) else None
                
                return NewspaperMetadata(
                    newspaper_name=newspaper_name,
                    publication_date=pub_date,
                    page_number=page_num
                )
            
            # Try alternative patterns
            # Pattern: YYYY-MM-DD_newspaper_name_page
            match = re.match(r'^(\d{4}-\d{2}-\d{2})_(.+?)(?:_p?(\d+))?$', filename)
            if match:
                pub_date = date.fromisoformat(match.group(1))
                newspaper_name = match.group(2).replace('_', ' ')
                page_num = int(match.group(3)) if match.group(3) else None
                
                return NewspaperMetadata(
                    newspaper_name=newspaper_name,
                    publication_date=pub_date,
                    page_number=page_num
                )
            
            logger.warning(f"Could not parse metadata from filename: {filename}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {filepath}: {e}")
            return None
    
    def clean_ocr_text(self, text: str) -> str:
        """Clean OCR artifacts from text."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        replacements = {
            r'\bl\b': 'I',  # lowercase L as I
            r'\bO\b': '0',  # O as zero in numbers
            r'(?<!\w)ll(?!\w)': 'II',  # ll as Roman numeral II
            r'(?<!\w)lll(?!\w)': 'III',  # lll as Roman numeral III
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Remove excessive line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    def chunk_text(
        self,
        text: str,
        metadata: NewspaperMetadata
    ) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        
        chunks = []
        words = text.split()
        
        if len(words) <= self.chunk_size:
            # Single chunk
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                content=text,
                newspaper_metadata=metadata,
                chunk_index=0,
                start_char=0,
                end_char=len(text)
            )
            chunks.append(chunk)
        else:
            # Multiple chunks with overlap
            chunk_index = 0
            char_offset = 0
            
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = ' '.join(chunk_words)
                
                # Calculate character positions
                start_char = char_offset
                end_char = start_char + len(chunk_text)
                
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=chunk_text,
                    newspaper_metadata=metadata,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char
                )
                chunks.append(chunk)
                
                # Update for next iteration
                chunk_index += 1
                # Account for spaces between words
                char_offset = text.find(words[min(i + self.chunk_size - self.chunk_overlap, len(words)-1)], char_offset)
        
        return chunks
    
    def process_file(self, filepath: Path) -> List[DocumentChunk]:
        """Process a single newspaper file."""
        try:
            # Extract metadata
            metadata = self.extract_metadata_from_filename(filepath)
            if not metadata:
                logger.warning(f"Skipping file without metadata: {filepath}")
                self.stats.failed_files += 1
                return []
            
            # Read and clean text
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
            
            logger.info(f"Processed {filepath.name}: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            self.stats.failed_files += 1
            return []
    
    def process_directory(
        self,
        directory: Path,
        file_pattern: str = "*.txt"
    ) -> List[DocumentChunk]:
        """Process all newspaper files in a directory."""
        all_chunks = []
        
        # Get all text files
        files = list(directory.glob(file_pattern))
        self.stats.total_files = len(files)
        
        logger.info(f"Found {len(files)} files to process")
        
        # Process each file
        for filepath in files:
            chunks = self.process_file(filepath)
            all_chunks.extend(chunks)
        
        # Sort newspapers list
        self.stats.newspapers.sort()
        
        logger.info(f"Processing complete: {self.stats.processed_files} files, "
                   f"{self.stats.total_chunks} chunks, {self.stats.failed_files} failures")
        
        return all_chunks
    
    def save_processing_stats(self, output_path: Path):
        """Save processing statistics to file."""
        stats_dict = self.stats.to_dict()
        with open(output_path, 'w') as f:
            json.dump(stats_dict, f, indent=2)
        logger.info(f"Saved processing stats to {output_path}")
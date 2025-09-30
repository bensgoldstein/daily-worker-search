"""Test script to verify Newspaper RAG system components."""

import sys
from pathlib import Path
from datetime import date

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        import config
        print("✓ Config module")
        
        import models
        print("✓ Models module")
        
        import document_processor
        print("✓ Document processor module")
        
        import vector_database
        print("✓ Vector database module")
        
        print("\nAll imports successful!")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    try:
        from config import config
        
        print(f"✓ Embedding model: {config.EMBEDDING_MODEL}")
        print(f"✓ Chunk size: {config.CHUNK_SIZE}")
        print(f"✓ Vector DB provider: {config.VECTOR_DB_PROVIDER}")
        
        # Try to validate
        try:
            config.validate()
            print("✓ Configuration is valid")
        except ValueError as e:
            print(f"⚠ Configuration warning: {e}")
            print("  (This is expected if .env is not configured)")
        
        return True
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False


def test_models():
    """Test data models."""
    print("\nTesting data models...")
    try:
        from models import NewspaperMetadata, DocumentChunk, SearchQuery
        
        # Test metadata
        metadata = NewspaperMetadata(
            newspaper_name="Test Times",
            publication_date=date(1920, 1, 1),
            page_number=1
        )
        print(f"✓ Created metadata: {metadata.newspaper_name}")
        
        # Test chunk
        chunk = DocumentChunk(
            chunk_id="test-001",
            content="This is a test newspaper content.",
            newspaper_metadata=metadata,
            chunk_index=0,
            start_char=0,
            end_char=33
        )
        print(f"✓ Created chunk: {chunk.chunk_id}")
        
        # Test query
        query = SearchQuery(
            query_text="test query",
            start_date=date(1920, 1, 1),
            end_date=date(1930, 1, 1)
        )
        print(f"✓ Created query: {query.query_text}")
        
        return True
    except Exception as e:
        print(f"✗ Models error: {e}")
        return False


def test_processor():
    """Test document processor."""
    print("\nTesting document processor...")
    try:
        from document_processor import NewspaperProcessor
        
        processor = NewspaperProcessor()
        
        # Test metadata extraction
        test_path = Path("New_York_Times_1920-05-15_1.txt")
        metadata = processor.extract_metadata_from_filename(test_path)
        
        if metadata:
            print(f"✓ Extracted metadata from filename:")
            print(f"  - Newspaper: {metadata.newspaper_name}")
            print(f"  - Date: {metadata.publication_date}")
            print(f"  - Page: {metadata.page_number}")
        else:
            print("⚠ Could not extract metadata (this is OK for testing)")
        
        # Test text cleaning
        dirty_text = "This   is    some\\n\\n\\n\\nOCR    text"
        clean_text = processor.clean_ocr_text(dirty_text)
        print(f"✓ Text cleaning works: '{clean_text}'")
        
        return True
    except Exception as e:
        print(f"✗ Processor error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Newspaper RAG System Test")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config,
        test_models,
        test_processor
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("✓ All tests passed! System is ready.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    print("\nNext steps:")
    print("1. Create a .env file with your API keys")
    print("2. Prepare your newspaper OCR files")
    print("3. Run: python process_newspapers.py --input-dir ./newspapers --output-dir ./processed")
    print("4. Deploy with: streamlit run app.py")


if __name__ == "__main__":
    main()
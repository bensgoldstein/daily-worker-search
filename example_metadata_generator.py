"""Example script to generate metadata files for newspaper OCR texts."""

import json
from datetime import date
from pathlib import Path
import argparse


def generate_metadata_example(txt_file: Path, newspaper_name: str, publication_date: str, page_number: int = None):
    """Generate a metadata JSON file for a newspaper text file."""
    
    metadata = {
        "newspaper_name": newspaper_name,
        "publication_date": publication_date,
        "page_number": page_number,
        "source_url": f"https://archive.org/details/{txt_file.stem}",
        "language": "en",
        "ocr_quality_score": 0.85  # Example score
    }
    
    # Save metadata file
    metadata_file = txt_file.with_suffix('.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Created metadata file: {metadata_file}")


def example_file_naming():
    """Show examples of proper file naming conventions."""
    
    print("Newspaper File Naming Conventions:")
    print("=" * 50)
    print("\nOption 1: newspaper_name_YYYY-MM-DD_page.txt")
    print("Examples:")
    print("  - New_York_Times_1920-05-15_1.txt")
    print("  - Chicago_Tribune_1945-08-15_12.txt")
    print("  - Los_Angeles_Times_1969-07-21.txt (no page number)")
    
    print("\nOption 2: YYYY-MM-DD_newspaper_name_page.txt")
    print("Examples:")
    print("  - 1920-05-15_New_York_Times_1.txt")
    print("  - 1945-08-15_Chicago_Tribune_12.txt")
    
    print("\nOption 3: Any naming + companion .json metadata file")
    print("Examples:")
    print("  - archive_scan_001.txt + archive_scan_001.json")
    print("  - nyt_19200515.txt + nyt_19200515.json")
    
    print("\nMetadata JSON format:")
    print(json.dumps({
        "newspaper_name": "New York Times",
        "publication_date": "1920-05-15",
        "page_number": 1,
        "section": "Front Page",
        "source_url": "https://archive.org/details/nyt_19200515",
        "ocr_quality_score": 0.92,
        "language": "en"
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Generate metadata for newspaper OCR files")
    parser.add_argument("--example", action="store_true", help="Show file naming examples")
    parser.add_argument("--generate", type=str, help="Generate metadata for a text file")
    parser.add_argument("--newspaper", type=str, help="Newspaper name")
    parser.add_argument("--date", type=str, help="Publication date (YYYY-MM-DD)")
    parser.add_argument("--page", type=int, help="Page number")
    
    args = parser.parse_args()
    
    if args.example:
        example_file_naming()
    elif args.generate:
        if not args.newspaper or not args.date:
            print("Error: --newspaper and --date are required when using --generate")
            return
        
        txt_file = Path(args.generate)
        if not txt_file.exists():
            print(f"Error: File not found: {txt_file}")
            return
        
        generate_metadata_example(txt_file, args.newspaper, args.date, args.page)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
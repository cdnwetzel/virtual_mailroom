#!/usr/bin/env python3
"""
CLI tool to split NY_INFO_SUBS_9.19.2025.pdf
"""
import sys
import os
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
import re
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_file_number(text):
    """Extract file number from text - looking for patterns like J2401735"""
    patterns = [
        r'Account\s+Number[.:]?\s*([JL]?\d{6,8})',
        r'File\s+No[.:]?\s*([JL]?\d{6,8})',
        r'Firm\s+File\s+No[.:]?\s*([JL]?\d{6,8})',
        r'Our\s+File\s+No[.:]?\s*([JL]?\d{6,8})',
        r'Account\s+#[.:]?\s*([JL]?\d{6,8})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            file_num = match.group(1).strip().upper()
            file_num = re.sub(r'[^A-Z0-9]', '', file_num)
            if len(file_num) >= 6:
                logger.debug(f"Found file number: {file_num}")
                return file_num
    return None

def split_is_document(input_pdf=None, output_dir="split_output", pages_per_doc=8):
    """
    Split IS document into individual PDFs
    Default: 8 pages per document (standard IS format)
    """

    # Default to the most recent temp file if no input provided
    if not input_pdf:
        input_pdf = "/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom/data/temp/temp_20250919_144944_NY_INFO_SUBS_9.19.2025.pdf"

    input_path = Path(input_pdf)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_pdf}")
        return False

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    complete_dir = output_path / "complete"
    incomplete_dir = output_path / "incomplete"
    complete_dir.mkdir(exist_ok=True)
    incomplete_dir.mkdir(exist_ok=True)

    logger.info(f"Processing: {input_path.name}")

    try:
        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        logger.info(f"Total pages: {total_pages}")
        logger.info(f"Splitting into {pages_per_doc}-page documents")

        # Extract all text for analysis
        all_text = []
        with pdfplumber.open(input_pdf) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                all_text.append(text)

                # Log file numbers found on each page
                if i < 32:  # Check first 32 pages
                    file_num = extract_file_number(text)
                    if file_num:
                        logger.info(f"  Page {i+1}: Found file number {file_num}")

        # Split and process
        results = []
        doc_count = 0
        complete_count = 0
        incomplete_count = 0
        file_number_counts = {}  # Track duplicates

        for start_page in range(0, total_pages, pages_per_doc):
            end_page = min(start_page + pages_per_doc, total_pages)
            doc_count += 1

            # Extract file number from document pages
            doc_text = "\n".join(all_text[start_page:end_page])
            file_number = extract_file_number(doc_text)

            # Create PDF writer
            writer = PdfWriter()
            for page_num in range(start_page, end_page):
                writer.add_page(reader.pages[page_num])

            # Determine output location and filename
            if file_number and not file_number.startswith('UNKNOWN'):
                # Handle duplicates by adding suffix
                file_number_counts[file_number] = file_number_counts.get(file_number, 0) + 1
                if file_number_counts[file_number] > 1:
                    output_file = complete_dir / f"{file_number}_IS_{file_number_counts[file_number]:02d}.pdf"
                else:
                    output_file = complete_dir / f"{file_number}_IS.pdf"
                complete_count += 1
                status = "✅ Complete"
            else:
                output_file = incomplete_dir / f"INCOMPLETE_{doc_count:02d}_IS.pdf"
                incomplete_count += 1
                status = "❌ Incomplete"

            # Write PDF
            with open(output_file, 'wb') as f:
                writer.write(f)

            logger.info(f"{status} Document {doc_count}: {output_file.name} (pages {start_page+1}-{end_page})")

            results.append({
                'document': doc_count,
                'filename': output_file.name,
                'file_number': file_number,
                'pages': f"{start_page+1}-{end_page}",
                'page_count': end_page - start_page,
                'status': 'complete' if file_number else 'incomplete'
            })

        # Save manifest
        manifest = {
            'processing_date': datetime.now().isoformat(),
            'input_file': input_path.name,
            'total_pages': total_pages,
            'pages_per_document': pages_per_doc,
            'total_documents': doc_count,
            'complete_documents': complete_count,
            'incomplete_documents': incomplete_count,
            'documents': results
        }

        manifest_file = output_path / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Print summary
        print("\n" + "="*60)
        print("SPLIT COMPLETE")
        print("="*60)
        print(f"Input file: {input_path.name}")
        print(f"Total pages: {total_pages}")
        print(f"Documents created: {doc_count}")
        print(f"  ✅ Complete (with file numbers): {complete_count}")
        print(f"  ❌ Incomplete (no file numbers): {incomplete_count}")
        print(f"\nOutput directory: {output_path}")
        print(f"  Complete documents: {complete_dir}")
        print(f"  Incomplete documents: {incomplete_dir}")
        print(f"  Manifest: {manifest_file}")
        print("="*60)

        return True

    except Exception as e:
        logger.error(f"Error during splitting: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Parse arguments
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "split_output"
    pages = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    success = split_is_document(input_file, output_dir, pages)
    sys.exit(0 if success else 1)
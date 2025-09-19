#!/usr/bin/env python3
"""
Fixed-page split for IS documents
IS documents are typically 7-8 pages each
"""
import sys
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_file_number(text):
    """Extract file number from text"""
    patterns = [
        r'Account\s+Number[.:]?\s*([A-Z]?\d{6,8})',
        r'File\s+No[.:]?\s*([A-Z]?\d{6,8})',
        r'Firm\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',
        r'Our\s+File\s+(?:Number|No)[.:]?\s*([A-Z]?\d{6,8})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            file_num = match.group(1).strip().upper()
            # Clean up file number
            file_num = re.sub(r'[^A-Z0-9]', '', file_num)
            if len(file_num) >= 6:
                return file_num
    return None

def split_is_fixed(input_pdf, output_dir="is_split_output", pages_per_doc=7):
    """Split IS document using fixed page counts"""

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    try:
        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        logger.info(f"Input PDF has {total_pages} pages")

        # Extract all text for file number detection
        all_text = []
        with pdfplumber.open(input_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text.append(text)

        doc_count = 0
        results = []

        for start_page in range(0, total_pages, pages_per_doc):
            end_page = min(start_page + pages_per_doc, total_pages)
            doc_count += 1

            # Extract file number from this document's pages
            doc_text = "\n".join(all_text[start_page:end_page])
            file_number = extract_file_number(doc_text)

            # Create output PDF
            writer = PdfWriter()
            for page_num in range(start_page, end_page):
                writer.add_page(reader.pages[page_num])

            # Output filename
            if file_number:
                output_file = output_path / f"{file_number}_IS.pdf"
                status = "Complete"
            else:
                output_file = output_path / f"INCOMPLETE_{doc_count:02d}_IS.pdf"
                status = "Incomplete (no file number)"

            with open(output_file, 'wb') as f:
                writer.write(f)

            logger.info(f"Created: {output_file.name} (pages {start_page+1}-{end_page}) - {status}")

            results.append({
                'filename': output_file.name,
                'pages': f"{start_page+1}-{end_page}",
                'file_number': file_number,
                'status': status
            })

        # Summary
        logger.info(f"\n✅ Split into {doc_count} documents")
        complete = sum(1 for r in results if r['file_number'])
        logger.info(f"Complete documents: {complete}/{doc_count}")
        logger.info(f"Output files saved in: {output_path}")

        return results

    except Exception as e:
        logger.error(f"Error during split: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    input_file = "/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom/data/temp/temp_20250919_144944_NY_INFO_SUBS_9.19.2025.pdf"

    # Try different page counts
    print("\n" + "=" * 60)
    print("Testing 7 pages per document:")
    print("=" * 60)
    results_7 = split_is_fixed(input_file, output_dir="is_split_7pages", pages_per_doc=7)

    print("\n" + "=" * 60)
    print("Testing 8 pages per document:")
    print("=" * 60)
    results_8 = split_is_fixed(input_file, output_dir="is_split_8pages", pages_per_doc=8)
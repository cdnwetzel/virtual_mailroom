#!/usr/bin/env python3
"""
Manual split for NY_INFO_SUBS_9.19.2025.pdf
Splits a 28-page IS document into 4 documents of 7 pages each
"""
import sys
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def manual_split_is(input_pdf, output_dir="manual_split_output"):
    """Manually split IS document into 7-page chunks"""

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    try:
        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        logger.info(f"Input PDF has {total_pages} pages")

        # IS documents are typically 7 pages each
        pages_per_doc = 7
        doc_count = 0

        for start_page in range(0, total_pages, pages_per_doc):
            end_page = min(start_page + pages_per_doc, total_pages)
            doc_count += 1

            writer = PdfWriter()
            for page_num in range(start_page, end_page):
                writer.add_page(reader.pages[page_num])

            # Output filename
            output_file = output_path / f"IS_Document_{doc_count:02d}_pages_{start_page+1}-{end_page}.pdf"

            with open(output_file, 'wb') as f:
                writer.write(f)

            logger.info(f"Created: {output_file.name} (pages {start_page+1}-{end_page})")

        logger.info(f"\n✅ Successfully split into {doc_count} documents")
        logger.info(f"Output files saved in: {output_path}")

        return True

    except Exception as e:
        logger.error(f"Error during manual split: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Use the most recent temp file
        input_file = "/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom/data/temp/temp_20250919_144944_NY_INFO_SUBS_9.19.2025.pdf"
        print(f"Using default file: {input_file}")
    else:
        input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    success = manual_split_is(input_file)
    sys.exit(0 if success else 1)
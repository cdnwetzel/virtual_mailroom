#!/usr/bin/env python3
"""
Repair script for LTD files where OCR missed the L prefix
Appends the second page to LTD documents
"""

import os
import sys
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def repair_ltd_file(input_pdf_path, output_dir, force_file_number=None):
    """
    Repair an LTD file by ensuring it has the proper second page appended
    """
    input_path = Path(input_pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(input_pdf_path)
        total_pages = len(reader.pages)

        if total_pages < 2:
            logger.warning(f"File {input_path.name} has less than 2 pages, skipping")
            return False

        # Extract the original filename parts
        filename = input_path.stem

        # If force_file_number is provided, use it
        if force_file_number:
            file_number = force_file_number.upper()
            # Ensure it starts with L if it doesn't already
            if not file_number.startswith('L') and not file_number.startswith('J'):
                file_number = 'L' + file_number
        else:
            # Try to extract file number from filename
            # Assuming format like UNKNOWN_001 or similar
            if 'UNKNOWN' in filename.upper():
                # This is a file that needs a proper L prefix
                parts = filename.split('_')
                if len(parts) > 1:
                    # Take the numeric part and add L prefix
                    numeric_part = ''.join(filter(str.isdigit, parts[-1]))
                    file_number = f"L{numeric_part}"
                else:
                    file_number = f"L{filename}"
            else:
                file_number = filename

        # Create output filename
        output_filename = f"LTD_{file_number}.pdf"
        output_path = output_dir / output_filename

        # Create new PDF with proper page arrangement
        writer = PdfWriter()

        # Add first page
        writer.add_page(reader.pages[0])

        # If there's a second page, ensure it's appended
        if total_pages >= 2:
            writer.add_page(reader.pages[1])

        # Add any remaining pages
        for i in range(2, total_pages):
            writer.add_page(reader.pages[i])

        # Write the repaired file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        logger.info(f"✅ Repaired: {input_path.name} -> {output_filename}")
        return True

    except Exception as e:
        logger.error(f"Error processing {input_path.name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Repair LTD files with missing L prefix')
    parser.add_argument('input', help='Input PDF file or directory containing PDFs to repair')
    parser.add_argument('-o', '--output', default='repaired', help='Output directory (default: repaired)')
    parser.add_argument('-f', '--file-number', help='Force specific file number (L will be added if missing)')

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if input_path.is_file():
        # Process single file
        success = repair_ltd_file(input_path, output_dir, args.file_number)
        if success:
            print(f"\nRepaired file saved to: {output_dir}")
        else:
            print("\nRepair failed")
            sys.exit(1)

    elif input_path.is_dir():
        # Process all PDFs in directory (both .pdf and .PDF)
        pdf_files = list(input_path.glob('*.pdf')) + list(input_path.glob('*.PDF'))
        if not pdf_files:
            print(f"No PDF files found in {input_path}")
            sys.exit(1)

        print(f"Found {len(pdf_files)} PDF files to repair")
        success_count = 0

        for pdf_file in pdf_files:
            if repair_ltd_file(pdf_file, output_dir):
                success_count += 1

        print(f"\n✅ Successfully repaired {success_count}/{len(pdf_files)} files")
        print(f"Repaired files saved to: {output_dir}")

    else:
        print(f"Error: {input_path} is not a valid file or directory")
        sys.exit(1)

if __name__ == "__main__":
    main()
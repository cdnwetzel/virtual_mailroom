#!/usr/bin/env python3
"""
Repair script for LTD files - appends template second page
"""

import os
import sys
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def repair_ltd_with_template(input_pdf_path, template_path, output_dir):
    """
    Repair an LTD file by appending the template second page
    """
    input_path = Path(input_pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(input_pdf_path)
        template_reader = PdfReader(template_path)

        if len(template_reader.pages) < 1:
            logger.error("Template file is empty")
            return False

        # Extract filename without extension
        filename = input_path.stem

        # Create output filename - keep the same name structure
        output_filename = f"{filename}.pdf"
        output_path = output_dir / output_filename

        # Create new PDF
        writer = PdfWriter()

        # Add all pages from original file
        for page in reader.pages:
            writer.add_page(page)

        # Add the template second page
        writer.add_page(template_reader.pages[0])

        # Write the repaired file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        logger.info(f"✅ Repaired: {input_path.name} -> {output_filename} (added second page)")
        return True

    except Exception as e:
        logger.error(f"Error processing {input_path.name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Repair LTD files by appending template second page')
    parser.add_argument('input', help='Input PDF file or directory containing PDFs to repair')
    parser.add_argument('-t', '--template', default='LTD_second_page_template.pdf',
                       help='Template second page file (default: LTD_second_page_template.pdf)')
    parser.add_argument('-o', '--output', default='repaired', help='Output directory (default: repaired)')

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    template_path = Path(args.template)

    if not template_path.exists():
        print(f"Error: Template file {template_path} not found")
        sys.exit(1)

    if input_path.is_file():
        # Process single file
        success = repair_ltd_with_template(input_path, template_path, output_dir)
        if success:
            print(f"\nRepaired file saved to: {output_dir}")
        else:
            print("\nRepair failed")
            sys.exit(1)

    elif input_path.is_dir():
        # Process all PDFs in directory
        pdf_files = list(input_path.glob('*.pdf')) + list(input_path.glob('*.PDF'))
        if not pdf_files:
            print(f"No PDF files found in {input_path}")
            sys.exit(1)

        print(f"Found {len(pdf_files)} PDF files to repair")
        print(f"Using template: {template_path}")
        success_count = 0

        for pdf_file in pdf_files:
            if repair_ltd_with_template(pdf_file, template_path, output_dir):
                success_count += 1

        print(f"\n✅ Successfully repaired {success_count}/{len(pdf_files)} files")
        print(f"Repaired files saved to: {output_dir}")

    else:
        print(f"Error: {input_path} is not a valid file or directory")
        sys.exit(1)

if __name__ == "__main__":
    main()
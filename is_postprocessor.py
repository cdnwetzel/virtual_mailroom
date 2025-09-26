#!/usr/bin/env python3
"""
Post-processor for IS documents to fix file numbers and apply corrections
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, Optional
import pdfplumber

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ISPostProcessor:
    """Post-process IS documents to extract and correct file numbers"""

    def apply_ocr_corrections(self, file_number: str) -> str:
        """Apply OCR corrections to file numbers"""
        if not file_number:
            return file_number

        # Fix first character if it's '1' and should be 'L'
        if len(file_number) >= 7 and file_number[0] == '1':
            if file_number[1:].isdigit() or (len(file_number) == 8 and file_number[1:].isdigit()):
                file_number = 'L' + file_number[1:]

        # Fix YL -> Y1 (second char should be 1 not L)
        if file_number.startswith('YL'):
            file_number = 'Y1' + file_number[2:]

        # Fix truncated file numbers (add missing zeros)
        if file_number.startswith('L') and len(file_number) == 7:
            # Check if it looks like L240029 should be L2400290
            if file_number[1:4].isdigit() and file_number[4:].isdigit():
                # Likely missing a trailing 0
                file_number = file_number + '0'

        return file_number

    def extract_file_number_comprehensive(self, pdf_path: Path) -> Optional[str]:
        """
        Comprehensive file number extraction from IS document
        Checks multiple pages and handles edge cases
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check first 3 pages for file number
                for page_idx in range(min(3, len(pdf.pages))):
                    text = pdf.pages[page_idx].extract_text() or ''

                    # Patterns to search for
                    patterns = [
                        r'File\s*No[.:]\s*([A-Z0-9]{6,8})',
                        r'Attorney.*\n.*File\s*No[.:]\s*([A-Z0-9]{6,8})',
                        # Handle truncated at line end
                        r'File\s*No[.:]\s*([A-Z0-9]{2,7})$',  # At end of line
                        r'Account\s*Number[.:]\s*([A-Z0-9]{6,8})',
                    ]

                    for pattern in patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                        for match in matches:
                            file_number = match.group(1).strip().upper()
                            # Apply corrections
                            file_number = self.apply_ocr_corrections(file_number)
                            if len(file_number) >= 6:  # Valid file number length
                                return file_number

                # Special case: check for truncated file numbers at page boundaries
                if len(pdf.pages) >= 2:
                    page2_text = pdf.pages[1].extract_text() or ''
                    lines = page2_text.split('\n')
                    for i, line in enumerate(lines):
                        if 'File No.' in line:
                            # Get this line and next few lines
                            file_num_text = line
                            for j in range(i + 1, min(i + 3, len(lines))):
                                file_num_text += ' ' + lines[j]

                            match = re.search(r'File\s*No[.:]\s*([A-Z0-9]{2,})', file_num_text, re.IGNORECASE)
                            if match:
                                file_number = match.group(1).strip().upper()
                                file_number = self.apply_ocr_corrections(file_number)
                                if len(file_number) >= 6:
                                    return file_number

        except Exception as e:
            logger.error(f"Error extracting from {pdf_path}: {e}")

        return None

    def process_directory(self, directory: str = "output"):
        """Process all IS documents in directory"""
        output_path = Path(directory)
        is_files = list(output_path.glob("IS_*.pdf"))

        if not is_files:
            logger.info("No IS files found to process")
            return

        logger.info(f"Processing {len(is_files)} IS documents")
        renamed_count = 0
        fixed_count = 0

        for pdf_file in is_files:
            # Skip if already has a valid file number
            if "UNKNOWN" not in pdf_file.name:
                # Check if needs correction (like YL -> Y1)
                current_file_num = pdf_file.stem.replace("IS_", "")
                corrected = self.apply_ocr_corrections(current_file_num)
                if corrected != current_file_num:
                    new_path = pdf_file.parent / f"IS_{corrected}.pdf"
                    if not new_path.exists():
                        os.rename(pdf_file, new_path)
                        logger.info(f"Corrected: {pdf_file.name} -> IS_{corrected}.pdf")
                        fixed_count += 1
                continue

            # Extract file number
            file_number = self.extract_file_number_comprehensive(pdf_file)

            if file_number:
                new_name = f"IS_{file_number}.pdf"
                new_path = pdf_file.parent / new_name

                if not new_path.exists():
                    os.rename(pdf_file, new_path)
                    logger.info(f"Renamed: {pdf_file.name} -> {new_name}")
                    renamed_count += 1
                else:
                    logger.warning(f"Cannot rename {pdf_file.name}: {new_name} already exists")
            else:
                logger.warning(f"Could not extract file number from {pdf_file.name}")

        logger.info(f"Post-processing complete: {renamed_count} renamed, {fixed_count} corrected")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Post-process IS documents')
    parser.add_argument('-d', '--directory', default='output',
                       help='Directory containing IS documents (default: output)')

    args = parser.parse_args()

    processor = ISPostProcessor()
    processor.process_directory(args.directory)


if __name__ == "__main__":
    main()
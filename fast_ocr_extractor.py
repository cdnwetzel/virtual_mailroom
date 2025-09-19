#!/usr/bin/env python3
"""
Fast OCR Extractor for File Numbers
Optimized for speed on large PDFs (up to 50MB)
"""

import re
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance
import concurrent.futures
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FastOCRExtractor:
    """Fast OCR extraction focused on file numbers"""

    def __init__(self):
        # File number patterns (1L+7N, 2L+6N, 8N)
        self.valid_patterns = [
            re.compile(r'^[A-Z]\d{7}$'),     # L2501375
            re.compile(r'^[A-Z]{2}\d{6}$'),  # JM221025
            re.compile(r'^\d{8}$'),          # 12345678
        ]

        # Quick OCR config for speed
        self.fast_config = "--psm 6 -c tessedit_do_invert=0 --oem 1"

    def quick_preprocess(self, image):
        """Minimal preprocessing for speed"""
        # Just grayscale and contrast
        image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        return image

    def extract_file_number_from_image(self, image) -> Optional[str]:
        """Extract file number from a single image"""
        try:
            # Quick preprocessing
            processed = self.quick_preprocess(image)

            # Crop to top portion where file numbers usually are
            width, height = processed.size
            cropped = processed.crop((0, 0, width, height // 3))

            # Run OCR on cropped region
            text = pytesseract.image_to_string(cropped, config=self.fast_config)

            # Clean common OCR errors
            text = text.replace('|', '1').replace('l', '1').replace('I', '1')
            text = text.replace('O', '0').replace('o', '0')

            # Look for file number patterns
            # Search near keywords first
            patterns = [
                r'File\s*No[.:]*\s*([A-Z0-9]{6,8})',
                r'Account\s*#?\s*([A-Z0-9]{6,8})',
                r'\b([A-Z]\d{7})\b',
                r'\b([A-Z]{2}\d{6})\b',
                r'\b(\d{8})\b',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text.upper(), re.MULTILINE)
                for match in matches:
                    cleaned = re.sub(r'[^A-Z0-9]', '', match)
                    # Validate against our patterns
                    for valid_pattern in self.valid_patterns:
                        if valid_pattern.match(cleaned):
                            return cleaned

        except Exception as e:
            logger.debug(f"Error processing image: {e}")

        return None

    def process_pdf_fast(self, pdf_path: Path, max_pages: int = 2) -> Optional[str]:
        """Fast PDF processing - only check first few pages"""
        try:
            start_time = time.time()
            logger.info(f"Processing: {pdf_path.name}")

            # Convert only first few pages at lower DPI for speed
            images = convert_from_path(
                pdf_path,
                dpi=200,  # Lower DPI for speed
                first_page=1,
                last_page=min(max_pages, 2),
                fmt='jpeg',
                thread_count=2
            )

            # Process pages
            for i, image in enumerate(images):
                file_number = self.extract_file_number_from_image(image)
                if file_number:
                    elapsed = time.time() - start_time
                    logger.info(f"  ✅ Found: {file_number} (page {i+1}, {elapsed:.1f}s)")
                    return file_number

            elapsed = time.time() - start_time
            logger.info(f"  ❌ No file number found ({elapsed:.1f}s)")
            return None

        except Exception as e:
            logger.error(f"  ⚠️  Error: {e}")
            return None

    def process_directory(self, input_dir: str):
        """Process all PDFs in directory"""
        input_path = Path(input_dir)
        pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))

        if not pdf_files:
            logger.error(f"No PDF files found in {input_dir}")
            return

        results = {
            "total": len(pdf_files),
            "success": 0,
            "files": {}
        }

        logger.info(f"Processing {len(pdf_files)} files with fast OCR")
        logger.info("="*50)

        for pdf_file in pdf_files:
            file_number = self.process_pdf_fast(pdf_file)
            results["files"][pdf_file.name] = file_number
            if file_number:
                results["success"] += 1

        # Print summary
        logger.info("="*50)
        logger.info("SUMMARY")
        logger.info("="*50)
        success_rate = (results["success"] / results["total"]) * 100 if results["total"] > 0 else 0
        logger.info(f"Success Rate: {results['success']}/{results['total']} ({success_rate:.1f}%)")

        logger.info("\nResults:")
        for filename, file_number in results["files"].items():
            if file_number:
                logger.info(f"  {filename}: {file_number}")
            else:
                logger.info(f"  {filename}: NOT FOUND")

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fast OCR extraction for file numbers')
    parser.add_argument('input', help='PDF file or directory to process')
    parser.add_argument('--pages', type=int, default=2, help='Max pages to check (default: 2)')

    args = parser.parse_args()

    extractor = FastOCRExtractor()

    input_path = Path(args.input)
    if input_path.is_file():
        file_number = extractor.process_pdf_fast(input_path, args.pages)
        if file_number:
            print(f"File Number: {file_number}")
        else:
            print("No file number found")
    elif input_path.is_dir():
        extractor.process_directory(args.input)
    else:
        logger.error(f"{args.input} is not a valid file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
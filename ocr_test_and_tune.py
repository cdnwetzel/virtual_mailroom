#!/usr/bin/env python3
"""
OCR Testing and Tuning Script for Virtual Mailroom
Tests different OCR configurations and preprocessing to improve accuracy
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import tempfile
from PIL import Image, ImageEnhance, ImageFilter
import pdfplumber
from PyPDF2 import PdfReader
import pytesseract

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OCRTester:
    """Test and tune OCR configurations for better accuracy"""

    def __init__(self):
        self.test_results = []

        # Known ground truth for testing
        self.ground_truth = {
            "INCOMPLETE_40651_07_IS.pdf": "Y1301388",
            "INCOMPLETE_629384_2024_IS.pdf": "L2401724",
            "INCOMPLETE_701405_2025_IS.pdf": "L2402234",
            "INCOMPLETE_710506_2024_IS.pdf": "JM2210250",
            "INCOMPLETE_EF20251433_IS.pdf": "L2500212",
        }

        # Various file number patterns to test
        self.file_patterns = [
            # Current patterns
            r'Our File Number:\s*([A-Z]{0,2}\d{1,8})',
            r'File Number:\s*([A-Z]{0,2}\d{1,8})',
            r'File #:\s*([A-Z]{0,2}\d{1,8})',
            r'File No[.:]?\s*([A-Z]{0,2}\d{1,8})',

            # Enhanced patterns for OCR issues
            r'File\s*No[.:]*\s*([A-Z]{0,2}[\s]*\d{1,8})',  # Allow space between letters and numbers
            r'Account\s*Number[:\s]*([A-Z]{0,2}\d{1,8})',
            r'Acct[.\s]*#?[:\s]*([A-Z]{0,2}\d{1,8})',
            r'Reference[:\s]*([A-Z]{0,2}\d{1,8})',

            # Patterns for OCR errors (0 vs O, 1 vs I, etc.)
            r'File\s*N[o0][.:]?\s*([A-Z0-9]{1,10})',
            r'F[i1]le\s*No[.:]?\s*([A-Z0-9]{1,10})',
        ]

    def extract_with_pdfplumber(self, pdf_path: str) -> List[str]:
        """Extract text using pdfplumber (current method)"""
        pages_text = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)
        except Exception as e:
            logger.error(f"PDFPlumber extraction error: {e}")
        return pages_text

    def extract_with_tesseract(self, pdf_path: str, config: str = "") -> List[str]:
        """Extract text using Tesseract OCR with different configurations"""
        pages_text = []
        try:
            # Convert PDF to images first
            from pdf2image import convert_from_path

            images = convert_from_path(pdf_path, dpi=300)

            for i, image in enumerate(images):
                # Apply preprocessing
                processed_image = self.preprocess_image(image)

                # Run OCR with specified config
                text = pytesseract.image_to_string(processed_image, config=config)
                pages_text.append(text)

        except Exception as e:
            logger.error(f"Tesseract extraction error: {e}")
        return pages_text

    def preprocess_image(self, image, enhance_level: str = "medium"):
        """Preprocess image for better OCR accuracy"""

        if enhance_level == "light":
            # Light preprocessing
            image = image.convert('L')  # Grayscale
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

        elif enhance_level == "medium":
            # Medium preprocessing
            image = image.convert('L')
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)

        elif enhance_level == "heavy":
            # Heavy preprocessing
            image = image.convert('L')
            # Denoise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.5)
            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)
            # Brightness adjustment
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)

        return image

    def test_file_number_extraction(self, text: str, patterns: List[str]) -> Optional[str]:
        """Test file number extraction with various patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                file_number = match.group(1).strip().upper()
                # Clean up OCR errors
                file_number = file_number.replace(' ', '')
                file_number = re.sub(r'[^A-Z0-9]', '', file_number)
                if len(file_number) <= 10 and len(file_number) >= 6:
                    return file_number
        return None

    def run_test_suite(self, test_dir: str = "ocr_training_data/incomplete_with_known_filenumbers"):
        """Run comprehensive OCR tests on known problematic files"""

        test_dir_path = Path(test_dir)
        if not test_dir_path.exists():
            logger.error(f"Test directory {test_dir} not found")
            return

        results = {
            "total_files": 0,
            "methods": {},
            "pattern_success": {},
            "file_results": {}
        }

        # Test configurations
        ocr_configs = [
            ("pdfplumber", None),
            ("tesseract_default", ""),
            ("tesseract_legacy", "--oem 0"),  # Legacy OCR engine
            ("tesseract_lstm", "--oem 1"),     # LSTM neural net
            ("tesseract_combined", "--oem 2"),  # Legacy + LSTM
            ("tesseract_psm3", "--psm 3"),      # Automatic page segmentation
            ("tesseract_psm6", "--psm 6"),      # Uniform block of text
            ("tesseract_psm11", "--psm 11"),    # Sparse text
        ]

        # Test each file
        for pdf_file in test_dir_path.glob("*.pdf"):
            filename = pdf_file.name
            expected = self.ground_truth.get(filename, "UNKNOWN")

            results["total_files"] += 1
            results["file_results"][filename] = {
                "expected": expected,
                "results": {}
            }

            logger.info(f"\nTesting {filename} (Expected: {expected})")

            # Try each OCR method
            for method_name, config in ocr_configs:
                if method_name not in results["methods"]:
                    results["methods"][method_name] = {"success": 0, "total": 0}

                results["methods"][method_name]["total"] += 1

                # Extract text based on method
                if method_name == "pdfplumber":
                    pages_text = self.extract_with_pdfplumber(str(pdf_file))
                else:
                    pages_text = self.extract_with_tesseract(str(pdf_file), config or "")

                # Try to find file number
                all_text = " ".join(pages_text)
                found_number = self.test_file_number_extraction(all_text, self.file_patterns)

                # Record result
                success = found_number == expected
                results["file_results"][filename]["results"][method_name] = {
                    "found": found_number,
                    "success": success
                }

                if success:
                    results["methods"][method_name]["success"] += 1
                    logger.info(f"  ✅ {method_name}: Found {found_number}")
                else:
                    logger.info(f"  ❌ {method_name}: Found {found_number or 'None'}")

        # Calculate success rates
        logger.info("\n" + "="*60)
        logger.info("RESULTS SUMMARY")
        logger.info("="*60)

        for method, stats in results["methods"].items():
            success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            logger.info(f"{method:20} {stats['success']}/{stats['total']} ({success_rate:.1f}%)")

        # Save detailed results
        output_file = "ocr_test_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nDetailed results saved to {output_file}")

        return results

    def suggest_improvements(self, results: Dict):
        """Suggest improvements based on test results"""

        logger.info("\n" + "="*60)
        logger.info("RECOMMENDATIONS")
        logger.info("="*60)

        # Find best performing method
        best_method = None
        best_rate = 0

        for method, stats in results["methods"].items():
            rate = (stats["success"] / stats["total"]) if stats["total"] > 0 else 0
            if rate > best_rate:
                best_rate = rate
                best_method = method

        if best_method:
            logger.info(f"1. Best OCR method: {best_method} ({best_rate*100:.1f}% success)")

        # Identify problem files
        problem_files = []
        for filename, file_data in results["file_results"].items():
            success_count = sum(1 for r in file_data["results"].values() if r["success"])
            if success_count == 0:
                problem_files.append(filename)

        if problem_files:
            logger.info(f"2. Problem files needing manual review: {', '.join(problem_files)}")

        # General recommendations
        logger.info("\n3. General improvements:")
        logger.info("   - Consider using Tesseract with PSM 3 or 6 for better results")
        logger.info("   - Preprocess images with contrast enhancement")
        logger.info("   - Add fallback patterns for common OCR errors (0/O, 1/I/l)")
        logger.info("   - Implement multi-method voting system for critical documents")


def main():
    """Run OCR testing and tuning"""
    import argparse

    parser = argparse.ArgumentParser(description='Test and tune OCR for Virtual Mailroom')
    parser.add_argument('--test-dir', default='ocr_training_data/incomplete_with_known_filenumbers',
                       help='Directory containing test PDFs')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test with fewer methods')

    args = parser.parse_args()

    tester = OCRTester()

    logger.info("Starting OCR Testing and Tuning")
    logger.info("================================")

    # Check for required tools
    try:
        subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
        logger.info("✅ Tesseract OCR installed")
    except:
        logger.warning("⚠️  Tesseract OCR not found. Install with: sudo apt-get install tesseract-ocr")

    try:
        import pdf2image
        logger.info("✅ pdf2image installed")
    except ImportError:
        logger.warning("⚠️  pdf2image not installed. Install with: pip install pdf2image")
        logger.warning("   Also need poppler-utils: sudo apt-get install poppler-utils")

    # Run tests
    results = tester.run_test_suite(args.test_dir)

    if results:
        tester.suggest_improvements(results)


if __name__ == "__main__":
    main()
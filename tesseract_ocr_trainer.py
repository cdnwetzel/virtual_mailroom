#!/usr/bin/env python3
"""
Tesseract OCR Training Script for Virtual Mailroom
Processes image-only PDFs to extract file numbers using OCR
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import subprocess
import tempfile
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pdf2image import convert_from_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TesseractOCRTrainer:
    """OCR trainer using Tesseract for image-only PDFs"""

    def __init__(self):
        # Expected file number formats
        self.pattern_rules = [
            (r'^[A-Z]\d{7}$', '1L+7N'),     # L2501375
            (r'^[A-Z]{2}\d{6}$', '2L+6N'),   # JM221025
            (r'^\d{8}$', '8N'),               # 12345678
        ]

        # OCR configurations to test
        self.ocr_configs = [
            ("default", ""),
            ("digits_focus", "--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            ("single_column", "--psm 4"),
            ("sparse_text", "--psm 11"),
            ("single_line", "--psm 7"),
            ("legacy", "--oem 0 --psm 6"),
        ]

        # Preprocessing methods to test
        self.preprocess_methods = [
            "none",
            "basic",
            "enhanced",
            "aggressive",
            "adaptive",
        ]

        self.results = []

    def preprocess_image(self, image, method="basic"):
        """Apply different preprocessing methods to improve OCR"""

        if method == "none":
            return image

        elif method == "basic":
            # Convert to grayscale and enhance contrast
            image = image.convert('L')
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            return image

        elif method == "enhanced":
            # Grayscale, denoise, contrast, sharpen
            image = image.convert('L')
            # Denoise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.5)
            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)
            return image

        elif method == "aggressive":
            # Heavy preprocessing for poor quality scans
            image = image.convert('L')

            # Resize for better OCR (if too small)
            width, height = image.size
            if width < 2000:
                scale = 2000 / width
                new_size = (int(width * scale), int(height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Binarization (convert to pure black and white)
            threshold = 128
            image = image.point(lambda p: p > threshold and 255)

            # Remove noise
            image = image.filter(ImageFilter.MedianFilter(size=3))

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(3.0)

            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)

            return image

        elif method == "adaptive":
            # Adaptive thresholding and enhancement
            import numpy as np
            import cv2

            # Convert PIL to OpenCV format
            image = image.convert('L')
            img_array = np.array(image)

            # Apply adaptive threshold
            img_thresh = cv2.adaptiveThreshold(
                img_array, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Denoise
            img_denoised = cv2.medianBlur(img_thresh, 3)

            # Morphological operations to clean up
            kernel = np.ones((1,1), np.uint8)
            img_morph = cv2.morphologyEx(img_denoised, cv2.MORPH_CLOSE, kernel)

            # Convert back to PIL
            image = Image.fromarray(img_morph)

            return image

        return image

    def extract_file_numbers_from_text(self, text: str) -> List[Tuple[str, str]]:
        """Extract potential file numbers from OCR text"""
        candidates = []

        # Clean up common OCR errors
        text = text.replace('|', '1')
        text = text.replace('l', '1')
        text = text.replace('O', '0')
        text = text.replace('o', '0')
        text = text.replace('S', '5')
        text = text.replace('Z', '2')

        # Search patterns in order of likelihood
        search_patterns = [
            # Near "File No." or similar
            r'File\s*No[.:]*\s*([A-Z0-9]{7,8})',
            r'File\s*#\s*([A-Z0-9]{7,8})',
            r'Account\s*#?\s*([A-Z0-9]{7,8})',

            # Standalone patterns matching our rules
            r'\b([A-Z]\d{7})\b',
            r'\b([A-Z]{2}\d{6})\b',
            r'\b(\d{8})\b',

            # With possible OCR errors (spaces)
            r'([A-Z]\s*\d{7})',
            r'([A-Z]{2}\s*\d{6})',
            r'(\d\s*\d{7})',
        ]

        for pattern in search_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean and validate
                cleaned = re.sub(r'\s+', '', match).upper()

                # Check if it matches our expected formats
                for rule_pattern, format_type in self.pattern_rules:
                    if re.match(rule_pattern, cleaned):
                        candidates.append((cleaned, format_type))
                        break

        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate[0] not in seen:
                seen.add(candidate[0])
                unique_candidates.append(candidate)

        return unique_candidates

    def process_pdf_with_ocr(self, pdf_path: Path, config: str, preprocess: str) -> List[str]:
        """Convert PDF to images and run OCR"""
        try:
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=300)

            all_text = []
            for i, image in enumerate(images):
                # Apply preprocessing
                processed_image = self.preprocess_image(image, preprocess)

                # Run OCR
                text = pytesseract.image_to_string(processed_image, config=config)
                all_text.append(text)

                # Focus on first 2 pages for file numbers
                if i >= 1:
                    break

            return all_text

        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return []

    def train_on_file(self, pdf_path: Path) -> Dict:
        """Train OCR configurations on a single file"""

        filename = pdf_path.name
        logger.info(f"\nProcessing: {filename}")

        file_results = {
            "filename": filename,
            "configurations": {},
            "best_config": None,
            "best_preprocess": None,
            "candidates_found": []
        }

        all_candidates = []

        # Test each preprocessing method
        for preprocess_method in self.preprocess_methods:
            # Test each OCR configuration
            for config_name, config_params in self.ocr_configs:
                config_key = f"{preprocess_method}_{config_name}"

                try:
                    # Run OCR
                    pages_text = self.process_pdf_with_ocr(pdf_path, config_params, preprocess_method)
                    full_text = "\n".join(pages_text)

                    # Extract file numbers
                    candidates = self.extract_file_numbers_from_text(full_text)

                    file_results["configurations"][config_key] = {
                        "text_length": len(full_text),
                        "candidates": candidates,
                        "success": len(candidates) > 0
                    }

                    if candidates:
                        all_candidates.extend(candidates)
                        logger.info(f"  ✅ {config_key}: Found {candidates[0][0]} ({candidates[0][1]})")

                except Exception as e:
                    logger.debug(f"  ❌ {config_key}: Error - {e}")
                    file_results["configurations"][config_key] = {"error": str(e)}

        # Find best configuration
        best_score = 0
        for config_key, result in file_results["configurations"].items():
            if "candidates" in result and result["candidates"]:
                score = len(result["candidates"])
                if score > best_score:
                    best_score = score
                    parts = config_key.split('_', 1)
                    file_results["best_preprocess"] = parts[0]
                    file_results["best_config"] = parts[1] if len(parts) > 1 else "default"

        # Get unique candidates
        seen = set()
        for candidate, format_type in all_candidates:
            if candidate not in seen:
                seen.add(candidate)
                file_results["candidates_found"].append({
                    "number": candidate,
                    "format": format_type
                })

        return file_results

    def run_training(self, input_dir: str):
        """Run OCR training on a directory of PDFs"""

        input_path = Path(input_dir)
        pdf_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))

        if not pdf_files:
            logger.error(f"No PDF files found in {input_dir}")
            return

        logger.info(f"Starting OCR training on {len(pdf_files)} files")
        logger.info("This may take a few minutes per file...")

        training_results = {
            "total_files": len(pdf_files),
            "successful_files": 0,
            "files": [],
            "best_configs": {},
            "best_preprocessing": {},
        }

        for pdf_file in pdf_files:
            file_result = self.train_on_file(pdf_file)
            training_results["files"].append(file_result)

            if file_result["candidates_found"]:
                training_results["successful_files"] += 1

                # Track best configurations
                if file_result["best_config"]:
                    config = file_result["best_config"]
                    training_results["best_configs"][config] = training_results["best_configs"].get(config, 0) + 1

                if file_result["best_preprocess"]:
                    preprocess = file_result["best_preprocess"]
                    training_results["best_preprocessing"][preprocess] = training_results["best_preprocessing"].get(preprocess, 0) + 1

        # Print summary
        self.print_summary(training_results)

        # Save results
        output_file = f"tesseract_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(training_results, f, indent=2)
        logger.info(f"\nDetailed results saved to {output_file}")

    def print_summary(self, results):
        """Print training summary"""

        logger.info("\n" + "="*60)
        logger.info("OCR TRAINING SUMMARY")
        logger.info("="*60)

        success_rate = (results["successful_files"] / results["total_files"]) * 100 if results["total_files"] > 0 else 0
        logger.info(f"Success Rate: {results['successful_files']}/{results['total_files']} ({success_rate:.1f}%)")

        if results["best_configs"]:
            logger.info("\nBest OCR Configurations:")
            for config, count in sorted(results["best_configs"].items(), key=lambda x: x[1], reverse=True)[:3]:
                logger.info(f"  {config}: {count} files")

        if results["best_preprocessing"]:
            logger.info("\nBest Preprocessing Methods:")
            for method, count in sorted(results["best_preprocessing"].items(), key=lambda x: x[1], reverse=True)[:3]:
                logger.info(f"  {method}: {count} files")

        logger.info("\nFile Numbers Found:")
        for file_data in results["files"]:
            if file_data["candidates_found"]:
                candidates_str = ", ".join([f"{c['number']} ({c['format']})" for c in file_data["candidates_found"][:3]])
                logger.info(f"  {file_data['filename']}: {candidates_str}")

        logger.info("\nRecommendations:")
        if results["best_preprocessing"]:
            best_preprocess = max(results["best_preprocessing"], key=results["best_preprocessing"].get)
            logger.info(f"1. Use '{best_preprocess}' preprocessing for best results")

        if results["best_configs"]:
            best_config = max(results["best_configs"], key=results["best_configs"].get)
            logger.info(f"2. Use '{best_config}' OCR configuration")

        if success_rate < 50:
            logger.info("3. Consider using Nitro Pro for initial OCR processing")
            logger.info("4. These files may need manual OCR or higher quality scans")


def check_dependencies():
    """Check if required dependencies are installed"""

    dependencies_ok = True

    # Check Tesseract
    try:
        subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
        logger.info("✅ Tesseract OCR installed")
    except:
        logger.error("❌ Tesseract not found. Install with: sudo apt-get install tesseract-ocr")
        dependencies_ok = False

    # Check Python packages
    try:
        import pytesseract
        logger.info("✅ pytesseract installed")
    except ImportError:
        logger.error("❌ pytesseract not installed. Install with: pip install pytesseract")
        dependencies_ok = False

    try:
        import pdf2image
        logger.info("✅ pdf2image installed")
    except ImportError:
        logger.error("❌ pdf2image not installed. Install with: pip install pdf2image")
        dependencies_ok = False

    try:
        subprocess.run(['pdftoppm', '-v'], capture_output=True, check=True)
        logger.info("✅ poppler-utils installed")
    except:
        logger.error("❌ poppler-utils not found. Install with: sudo apt-get install poppler-utils")
        dependencies_ok = False

    return dependencies_ok


def main():
    import argparse

    parser = argparse.ArgumentParser(description='OCR training for file number extraction')
    parser.add_argument('input_dir', help='Directory containing PDF files to process')
    parser.add_argument('--check-only', action='store_true', help='Only check dependencies')

    args = parser.parse_args()

    logger.info("Tesseract OCR Training Script")
    logger.info("="*40)

    if not check_dependencies():
        logger.error("\nPlease install missing dependencies before running training")
        return

    if args.check_only:
        logger.info("\nDependencies check complete")
        return

    trainer = TesseractOCRTrainer()
    trainer.run_training(args.input_dir)


if __name__ == "__main__":
    main()
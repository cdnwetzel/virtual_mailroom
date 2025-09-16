#!/usr/bin/env python3
"""
Analyze incomplete documents to find potential file numbers we might be missing
"""

import os
import re
import sys
from pathlib import Path
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import tempfile

def extract_text_with_ocr(pdf_path, page_num):
    """Extract text from a page using OCR"""
    try:
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            return ""

        page = doc[page_num]
        # Full page at high resolution for better OCR
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        # Convert to PIL Image
        img_data = pix.tobytes("png")

        # Create temp file for OCR
        temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_img.write(img_data)
        temp_img.close()

        # Perform OCR
        text = pytesseract.image_to_string(Image.open(temp_img.name))

        # Cleanup
        os.unlink(temp_img.name)
        doc.close()

        return text

    except Exception as e:
        print(f"OCR error on page {page_num}: {e}")
        return ""

def extract_regular_text(pdf_path, page_num):
    """Extract regular text from PDF"""
    try:
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            return ""

        page = doc[page_num]
        text = page.get_text()
        doc.close()
        return text

    except Exception as e:
        print(f"Text extraction error on page {page_num}: {e}")
        return ""

def find_potential_file_numbers(text):
    """Look for potential file number patterns"""
    patterns = [
        # Current strict patterns
        r'Firm\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',
        r'File\s+No[.:]?\s*([A-Z]?\d{6,8})',
        r'Our\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',
        r'Attorney\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',
        r'Client\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',

        # More flexible patterns to catch variations
        r'File\s+No[.:]?\s*([A-Z]?\d{4,8}[/-]?\d{0,4})',  # With slashes/hyphens
        r'File\s*#\s*([A-Z]?\d{4,8})',  # File # format
        r'Reference\s*#?\s*([A-Z]?\d{6,8})',  # Reference number
        r'Account\s*#?\s*([A-Z]?\d{6,8})',  # Account number
        r'Matter\s*#?\s*([A-Z]?\d{6,8})',  # Matter number

        # Broader search for any standalone numbers that might be file numbers
        r'(?:^|\s)([A-Z]?\d{6,8})(?:\s|$)',  # Standalone 6-8 digit numbers
    ]

    found = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            found.append({
                'pattern': pattern,
                'match': match.group(1),
                'context': text[max(0, match.start()-50):match.end()+50].replace('\n', ' ')
            })

    return found

def analyze_incomplete_document(pdf_path):
    """Analyze an incomplete document for potential file numbers"""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {os.path.basename(pdf_path)}")
    print(f"{'='*80}")

    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()

        all_findings = []

        # Check first few pages with both regular text and OCR
        pages_to_check = min(5, total_pages)

        for page_num in range(pages_to_check):
            print(f"\n--- PAGE {page_num + 1} ---")

            # Try regular text extraction first
            regular_text = extract_regular_text(pdf_path, page_num)
            if regular_text.strip():
                print(f"Regular text extraction successful ({len(regular_text)} chars)")
                findings = find_potential_file_numbers(regular_text)
                if findings:
                    print("POTENTIAL FILE NUMBERS FOUND (Regular Text):")
                    for finding in findings:
                        print(f"  Match: {finding['match']}")
                        print(f"  Context: ...{finding['context']}...")
                        all_findings.append(finding)

            # Try OCR extraction
            ocr_text = extract_text_with_ocr(pdf_path, page_num)
            if ocr_text.strip():
                print(f"OCR text extraction successful ({len(ocr_text)} chars)")
                findings = find_potential_file_numbers(ocr_text)
                if findings:
                    print("POTENTIAL FILE NUMBERS FOUND (OCR):")
                    for finding in findings:
                        print(f"  Match: {finding['match']}")
                        print(f"  Context: ...{finding['context']}...")
                        all_findings.append(finding)

            if not regular_text.strip() and not ocr_text.strip():
                print("No text extracted from this page")

        if not all_findings:
            print("\n❌ NO POTENTIAL FILE NUMBERS FOUND")
        else:
            print(f"\n✅ FOUND {len(all_findings)} POTENTIAL PATTERNS")

    except Exception as e:
        print(f"Error analyzing {pdf_path}: {e}")

def main():
    """Main function"""
    incomplete_dir = "/home/psadmin/ai/virtual_mailroom/corrected_final_output/incomplete"

    # Get all incomplete PDF files
    pdf_files = [f for f in os.listdir(incomplete_dir) if f.endswith('.pdf')]
    pdf_files.sort()

    print(f"Found {len(pdf_files)} incomplete documents to analyze")

    for pdf_file in pdf_files:
        pdf_path = os.path.join(incomplete_dir, pdf_file)
        analyze_incomplete_document(pdf_path)

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
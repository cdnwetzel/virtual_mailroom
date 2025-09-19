#!/usr/bin/env python3
"""
Analyze IS document content to understand why boundaries aren't being detected
"""
import pdfplumber
from pathlib import Path
import re

def analyze_is_content():
    """Analyze the content of the IS PDF to find markers"""

    input_file = "/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom/data/temp/temp_20250919_144944_NY_INFO_SUBS_9.19.2025.pdf"

    print(f"Analyzing: {input_file}")
    print("=" * 60)

    with pdfplumber.open(input_file) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        print("\nSearching for IS markers...\n")

        # Check first few pages of each potential document
        for page_num in [0, 1, 7, 8, 14, 15, 21, 22, 28, 29]:
            if page_num < len(pdf.pages):
                print(f"\n--- Page {page_num + 1} ---")
                page = pdf.pages[page_num]
                text = page.extract_text() or ""

                # Show first 500 chars
                preview = text[:500].replace('\n', ' ')
                print(f"Text preview: {preview}")

                # Check for IS markers
                if "INFORMATION SUBPOENA" in text.upper():
                    print("✅ Found 'INFORMATION SUBPOENA'")
                if "RESTRAINING NOTICE" in text.upper():
                    print("✅ Found 'RESTRAINING NOTICE'")

                # Check for file numbers
                file_patterns = [
                    r'File\s+No[.:]?\s*([A-Z]?\d{6,8})',
                    r'Firm\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',
                    r'Our\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',
                    r'Account\s+Number[.:]?\s*([A-Z]?\d{6,8})',
                ]

                for pattern in file_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        print(f"📁 Found file number pattern: {match.group()}")

                # Check for Index numbers
                index_patterns = [
                    r'Index\s+No[.:]?\s*([A-Z0-9\-/]+)',
                    r'Case\s+No[.:]?\s*([A-Z0-9\-/]+)',
                ]

                for pattern in index_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        print(f"📋 Found index number: {match.group()}")

        # Check if document is scanned (no text)
        print("\n\nChecking if document is scanned...")
        empty_pages = 0
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if len(text.strip()) < 50:
                empty_pages += 1

        if empty_pages > len(pdf.pages) / 2:
            print(f"⚠️ Document appears to be scanned ({empty_pages}/{len(pdf.pages)} pages have no text)")
            print("OCR may be needed for proper processing")
        else:
            print(f"✅ Document has text ({len(pdf.pages) - empty_pages}/{len(pdf.pages)} pages have text)")

if __name__ == "__main__":
    analyze_is_content()
#!/usr/bin/env python3
"""
Test enhanced file number patterns against known examples
"""

import re

# Enhanced patterns from infosub_processor.py
file_patterns = [
    r'Firm\s+File\s+No[.:]?\s*([A-Z]{0,2}\d{6,8})',  # Firm File No. - conclusive IS pattern
    r'File\s+No[.:]?\s*([A-Z]{0,2}\d{6,8})',  # File No. with 0-2 letter prefix
    r'File\s+Number[.:]?\s*([A-Z]{0,2}\d{6,8})',  # File Number
    r'Our\s+File\s+No[.:]?\s*([A-Z]{0,2}\d{6,8})',  # Our File No
    r'Attorney\s+File\s+No[.:]?\s*([A-Z]{0,2}\d{6,8})',  # Attorney File No
    r'Client\s+File\s+No[.:]?\s*([A-Z]{0,2}\d{6,8})',  # Client File No
    # Account Number patterns found in analysis (L prefix examples)
    r'Account\s+Number[.:]?\s*([A-Z]{0,2}\d{6,8})',  # Account Number
    r'Account\s+No[.:]?\s*([A-Z]{0,2}\d{6,8})',  # Account No
    # More flexible patterns for various formats
    r'(?:Firm|File|Our|Attorney|Client)\s+(?:File\s+)?No[.:]?\s*([A-Z]{0,2}\d{6,8})',
    r'(?:File|Firm)\s*#\s*([A-Z]{0,2}\d{6,8})',  # File # format
]

def extract_file_number(text):
    """Extract file number from text using enhanced patterns"""
    for pattern in file_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            file_number = match.group(1)
            return file_number
    return None

# Test cases from analyze_incomplete.py findings
test_cases = [
    ("File No. L2500212", "L2500212"),
    ("Account Number: L2402446", "L2402446"),
    ("File No. 12402446", "12402446"),
    ("File No. Y1301388", "Y1301388"),
    ("Account Number: L2401742", "L2401742"),
    ("File No. 12401742", "12401742"),
    ("File No. 12402234", "12402234"),
    ("File No. JM2210250", "JM2210250"),  # JM prefix pattern
    ("Firm File No. 12345678", "12345678"),
    ("Our File No: 87654321", "87654321"),
]

print("Testing enhanced file number patterns...")
print("=" * 60)

for i, (test_text, expected) in enumerate(test_cases, 1):
    result = extract_file_number(test_text)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    print(f"Test {i}: {status}")
    print(f"  Text: '{test_text}'")
    print(f"  Expected: {expected}")
    print(f"  Got: {result}")
    print()

print("Pattern testing complete.")
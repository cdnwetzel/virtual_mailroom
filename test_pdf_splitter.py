#!/usr/bin/env python3
"""
Test script for Virtual Mailroom PDF Splitter
"""

import os
import sys
from pathlib import Path
from PyPDF2 import PdfWriter, PdfReader
import random
import string

def create_test_pdf(filename: str, num_pages: int = 5):
    """Create a test PDF with sample content"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    c = canvas.Canvas(filename, pagesize=letter)
    
    for page_num in range(num_pages):
        file_num = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
                  ''.join(random.choices(string.digits, k=7))
        
        debtor_names = ["John Doe", "Jane Smith", "ABC Corporation", "XYZ Holdings LLC"]
        debtor = random.choice(debtor_names)
        
        jurisdictions = ["New York, NY", "Newark, NJ", "Brooklyn, NY", "Jersey City, NJ"]
        jurisdiction = random.choice(jurisdictions)
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, f"LEGAL NOTICE - Page {page_num + 1}")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"Our File Number: {file_num}")
        c.drawString(100, 680, f"To: {debtor}")
        c.drawString(100, 660, f"123 Main Street")
        c.drawString(100, 640, f"{jurisdiction} 10001")
        
        c.drawString(100, 600, "Re: Registration of Filing")
        
        c.setFont("Helvetica", 10)
        text = [
            "This is to notify you that your case has been registered.",
            "Please respond within 30 days of receiving this notice.",
            "",
            "Important: This is a legal document requiring your attention.",
            "Failure to respond may result in default judgment."
        ]
        
        y_pos = 560
        for line in text:
            c.drawString(100, y_pos, line)
            y_pos -= 20
        
        if page_num == 0:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, 400, "URGENT: Response required immediately")
        
        c.drawString(100, 100, f"Page {page_num + 1} of {num_pages}")
        c.showPage()
    
    c.save()
    print(f"Created test PDF: {filename}")

def test_basic_split():
    """Test basic PDF splitting"""
    print("\n=== Testing Basic PDF Split ===")
    
    from pdf_splitter import PDFSplitter
    
    test_file = "test_multi_page.pdf"
    create_test_pdf(test_file, num_pages=6)
    
    splitter = PDFSplitter(output_dir="test_output")
    results = splitter.split_pdf(test_file, pages_per_doc=2)
    
    print(f"Split into {len(results)} documents")
    for doc in results:
        print(f"  - {doc['output_file']}: {doc['pages']}")
    
    os.remove(test_file)
    return len(results) == 3

def test_auto_detection():
    """Test auto-detection of document boundaries"""
    print("\n=== Testing Auto-Detection ===")
    
    from pdf_splitter import PDFSplitter
    
    test_file = "test_auto_detect.pdf"
    create_test_pdf(test_file, num_pages=5)
    
    splitter = PDFSplitter(output_dir="test_output")
    results = splitter.split_pdf(test_file, auto_detect=True)
    
    print(f"Auto-detected {len(results)} documents")
    for doc in results:
        print(f"  - File Number: {doc['file_number']}")
        print(f"    Debtor: {doc['debtor_name']}")
        print(f"    Type: {doc['document_type']}")
    
    os.remove(test_file)
    return len(results) > 0

def test_pattern_extraction():
    """Test pattern extraction"""
    print("\n=== Testing Pattern Extraction ===")
    
    from pdf_splitter import PDFSplitter
    
    splitter = PDFSplitter()
    
    test_cases = [
        ("Our File Number: A1234567", "A1234567"),
        ("File #: B987654", "B987654"),
        ("Case Number: 12345678", "12345678"),
        ("To: John Doe", "John Doe"),
        ("To: ABC Corporation LLC", "ABC Corporation LLC")
    ]
    
    passed = 0
    for text, expected in test_cases:
        if "File" in text or "Case" in text:
            result = splitter.extract_file_number(text)
        else:
            result = splitter.extract_debtor_name(text)
        
        if result == expected:
            print(f"  ✓ Extracted '{result}' from '{text}'")
            passed += 1
        else:
            print(f"  ✗ Failed to extract from '{text}' (got '{result}')")
    
    return passed == len(test_cases)

def test_chatps_integration():
    """Test ChatPS integration"""
    print("\n=== Testing ChatPS Integration ===")
    
    try:
        from mailroom_chatps_integration import ChatPSConnector, ChatPSEnvironment
        
        connector = ChatPSConnector(ChatPSEnvironment.NEXTGEN)
        
        if connector.verify_connection():
            print("  ✓ Connected to ChatPS")
            
            test_text = """
            Our File Number: A1234567
            To: John Doe
            Re: Registration of Filing
            URGENT: Response required
            """
            
            result = connector.extract_structured_data(test_text)
            if result:
                print("  ✓ Data extraction working")
            else:
                print("  ⚠ Data extraction returned empty result")
            
            doc_type, confidence = connector.classify_document(test_text)
            print(f"  ✓ Classification: {doc_type} ({confidence:.2%} confidence)")
            
            return True
        else:
            print("  ⚠ ChatPS not available - skipping integration tests")
            return False
            
    except Exception as e:
        print(f"  ⚠ Integration test skipped: {e}")
        return False

def cleanup_test_files():
    """Clean up test output"""
    import shutil
    
    if Path("test_output").exists():
        shutil.rmtree("test_output")
        print("\nCleaned up test output directory")

def main():
    """Run all tests"""
    print("="*60)
    print("Virtual Mailroom Test Suite")
    print("="*60)
    
    tests = [
        ("Basic Split", test_basic_split),
        ("Auto Detection", test_auto_detection),
        ("Pattern Extraction", test_pattern_extraction),
        ("ChatPS Integration", test_chatps_integration)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ {name} failed with error: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:20} {status}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    cleanup_test_files()
    
    return passed_count == total_count

if __name__ == "__main__":
    try:
        import reportlab
    except ImportError:
        print("Installing reportlab for test PDF generation...")
        os.system("pip install reportlab")
    
    success = main()
    sys.exit(0 if success else 1)
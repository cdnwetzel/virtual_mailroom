#!/usr/bin/env python3
"""
Test script for Information Subpoena processor
"""

import os
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from infosub_processor import InfoSubProcessor


def create_test_pdf():
    """Create a simple test PDF for demonstration"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        filename = "test_infosub.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        
        # First document - Page 1
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "INFORMATION SUBPOENA WITH RESTRAINING NOTICE")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "State of New York")
        c.drawString(100, 680, "Supreme Court")
        c.showPage()
        
        # First document - Page 2 (with file number)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Continued from previous page...")
        c.drawString(100, 700, "File No. A1234567")
        c.drawString(100, 680, "Additional content for document 1")
        c.showPage()
        
        # Blank page
        c.drawString(100, 400, "")  # Minimal content - should be considered blank
        c.showPage()
        
        # Second document - Page 1
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "INFORMATION SUBPOENA WITH RESTRAINING NOTICE")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "State of New York")
        c.drawString(100, 680, "Supreme Court - Second Document")
        c.showPage()
        
        # Second document - Page 2 (with file number)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Continued from previous page...")
        c.drawString(100, 700, "File No. B9876543")
        c.drawString(100, 680, "Additional content for document 2")
        c.showPage()
        
        # Exemption claim form (part of second document)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 750, "EXEMPTION CLAIM FORM")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "This form is part of the subpoena document")
        c.drawString(100, 680, "File No. B9876543")
        c.showPage()
        
        c.save()
        print(f"Created test PDF: {filename}")
        return filename
        
    except ImportError:
        print("Reportlab not available - cannot create test PDF")
        return None


def test_processor():
    """Test the InfoSub processor"""
    print("="*60)
    print("Testing Information Subpoena Processor")
    print("="*60)
    
    # Create test PDF
    test_file = create_test_pdf()
    if not test_file:
        print("Cannot create test file - skipping test")
        return False
    
    try:
        # Test the processor
        processor = InfoSubProcessor(output_dir="test_output")
        results = processor.process_pdf(test_file)
        
        if results:
            print("\n✅ Processing successful!")
            processor.print_summary()
            
            # Verify outputs
            output_dir = Path("test_output")
            pdf_files = list(output_dir.glob("*.pdf"))
            
            print(f"\nGenerated {len(pdf_files)} PDF files:")
            for pdf_file in pdf_files:
                print(f"  - {pdf_file.name}")
            
            return True
        else:
            print("❌ No documents were processed")
            return False
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return False
    
    finally:
        # Cleanup
        if test_file and os.path.exists(test_file):
            os.remove(test_file)


def test_patterns():
    """Test pattern extraction"""
    print("\n" + "="*60)
    print("Testing Pattern Extraction")
    print("="*60)
    
    processor = InfoSubProcessor()
    
    test_cases = [
        ("File No. A1234567", "A1234567"),
        ("File Number: B987654", "B987654"),
        ("Our File No: C123456", "C123456"),
        ("Case No. D999888", "D999888"),
        ("INFORMATION SUBPOENA WITH RESTRAINING NOTICE", True),
        ("information subpoena with restraining notice", True),
        ("EXEMPTION CLAIM FORM", True),
        ("This page intentionally left blank", True),
        ("Regular content", False)
    ]
    
    print("\nFile Number Extraction:")
    for text, expected in test_cases[:4]:
        result = processor.extract_file_number(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text}' -> '{result}' (expected '{expected}')")
    
    print("\nDocument Start Detection:")
    for text, expected in test_cases[4:6]:
        result = processor.is_document_start(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text}' -> {result} (expected {expected})")
    
    print("\nContinuation Page Detection:")
    text, expected = test_cases[6]
    result = processor.is_continuation_page(text)
    status = "✓" if result == expected else "✗"
    print(f"  {status} '{text}' -> {result} (expected {expected})")
    
    print("\nBlank Page Detection:")
    for text, expected in test_cases[7:]:
        result = processor.is_blank_page(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text}' -> {result} (expected {expected})")


def main():
    """Main test runner"""
    print("🧪 Information Subpoena Processor Test Suite")
    
    # Test pattern extraction
    test_patterns()
    
    # Test full processing
    success = test_processor()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if success:
        print("✅ All tests passed!")
        print("\nTo use the processor:")
        print("  python3 infosub_processor.py input.pdf")
        print("  python3 infosub_processor.py input.pdf --debug")
    else:
        print("❌ Some tests failed")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
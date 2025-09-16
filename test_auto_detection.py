#!/usr/bin/env python3
"""
Test auto-detection between LTD and IS documents
"""

import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from document_detector import DocumentTypeDetector


def test_detection_patterns():
    """Test detection logic with text samples"""
    print("="*60)
    print("Testing Document Type Detection Patterns")
    print("="*60)
    
    detector = DocumentTypeDetector()
    
    # Test cases: (text_sample, expected_type, description)
    test_cases = [
        (
            "INFORMATION SUBPOENA WITH RESTRAINING NOTICE\nState of New York\nSupreme Court",
            "IS",
            "Information Subpoena - uppercase"
        ),
        (
            "information subpoena with restraining notice\nFile No. A1234567",
            "IS", 
            "Information Subpoena - lowercase"
        ),
        (
            "Our File Number: A1234567\nTo: John Doe\n123 Main Street",
            "LTD",
            "Legal/Debt Collection document"
        ),
        (
            "File Number: B987654\nNotice of Legal Action",
            "LTD",
            "Legal Notice document"
        ),
        (
            "Some random document content\nNo specific patterns here",
            "UNKNOWN",
            "No recognizable patterns"
        ),
        (
            "EXEMPTION CLAIM FORM\nFile No. C123456\nThis is part of subpoena",
            "IS",
            "Exemption claim form (IS secondary pattern)"
        )
    ]
    
    passed = 0
    total = len(test_cases)
    
    for text, expected, description in test_cases:
        # Create temporary "analysis" by checking patterns directly
        is_score = 0
        ltd_score = 0
        
        # Check IS patterns
        for pattern in detector.is_patterns:
            if pattern in text:
                is_score += 1.0
        
        for pattern in detector.is_secondary:
            if pattern in text:
                is_score += 0.3
        
        # Check LTD patterns  
        for pattern in detector.ltd_patterns:
            if pattern in text:
                ltd_score += 0.5
        
        # Simple decision logic
        if is_score > 0:
            detected = "IS"
        elif ltd_score > 0:
            detected = "LTD"
        else:
            detected = "UNKNOWN"
        
        status = "✓" if detected == expected else "✗"
        print(f"{status} {description}")
        print(f"    Expected: {expected}, Got: {detected}")
        print(f"    Scores - IS: {is_score:.1f}, LTD: {ltd_score:.1f}")
        
        if detected == expected:
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    return passed == total


def create_test_pdfs():
    """Create test PDFs for validation"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # Create IS test PDF
        is_filename = "test_is_doc.pdf"
        c = canvas.Canvas(is_filename, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "INFORMATION SUBPOENA WITH RESTRAINING NOTICE")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "State of New York Supreme Court")
        c.showPage()
        c.drawString(100, 750, "File No. A1234567")
        c.drawString(100, 700, "Continued from previous page")
        c.save()
        
        # Create LTD test PDF
        ltd_filename = "test_ltd_doc.pdf"
        c = canvas.Canvas(ltd_filename, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Our File Number: B987654")
        c.drawString(100, 700, "To: John Doe")
        c.drawString(100, 680, "123 Main Street")
        c.drawString(100, 660, "New York, NY 10001")
        c.drawString(100, 620, "Re: Legal Notice")
        c.save()
        
        return [is_filename, ltd_filename]
        
    except ImportError:
        print("Reportlab not available - skipping PDF creation")
        return []


def test_pdf_detection():
    """Test detection with actual PDF files"""
    print("="*60)
    print("Testing PDF Document Detection")
    print("="*60)
    
    test_files = create_test_pdfs()
    
    if not test_files:
        print("No test PDFs created - skipping PDF tests")
        return True
    
    detector = DocumentTypeDetector()
    
    expected_results = {
        "test_is_doc.pdf": "IS",
        "test_ltd_doc.pdf": "LTD"
    }
    
    passed = 0
    total = len(test_files)
    
    for filename in test_files:
        if Path(filename).exists():
            detected_type = detector.quick_detect(filename)
            expected = expected_results.get(filename, "UNKNOWN")
            
            status = "✓" if detected_type == expected else "✗"
            print(f"{status} {filename}: Expected {expected}, Got {detected_type}")
            
            if detected_type == expected:
                passed += 1
            
            # Cleanup
            Path(filename).unlink()
        else:
            print(f"✗ {filename}: File not found")
    
    print(f"\nResults: {passed}/{total} PDF tests passed")
    return passed == total


def main():
    """Run all tests"""
    print("🔍 Document Auto-Detection Test Suite")
    print("Testing LTD vs IS document type detection")
    
    # Test pattern detection
    patterns_ok = test_detection_patterns()
    
    # Test PDF detection
    pdfs_ok = test_pdf_detection()
    
    print("\n" + "="*60)
    print("OVERALL RESULTS")
    print("="*60)
    
    if patterns_ok and pdfs_ok:
        print("✅ All tests passed!")
        print("\nAuto-detection should work correctly:")
        print("  - Information Subpoenas → InfoSub processor")
        print("  - Legal/Debt documents → Standard PDF splitter")
        print("  - Unknown documents → Standard PDF splitter (fallback)")
        
        print("\nIn the Virtual Mailroom UI:")
        print("  1. Select 'Auto-Detect' from document type dropdown")
        print("  2. Upload mixed PDFs with IS and LTD documents")
        print("  3. System will automatically route each to correct processor")
    else:
        print("❌ Some tests failed - check detection logic")
    
    return patterns_ok and pdfs_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
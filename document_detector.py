#!/usr/bin/env python3
"""
Document Type Auto-Detection
Analyzes PDF content to determine if it's LTD or IS document type
"""

import pdfplumber
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DocumentTypeDetector:
    """Detects document types from PDF content"""
    
    def __init__(self):
        """Initialize detector with patterns"""
        # Information Subpoena patterns (check first - more specific)
        self.is_patterns = [
            "INFORMATION SUBPOENA WITH RESTRAINING NOTICE",
            "information subpoena with restraining notice"
        ]
        
        # LTD (Legal/Debt Collection) patterns
        self.ltd_patterns = [
            "Our File Number:",
            "our file number:",
            "File Number:",
            "file number:",
            "To:",  # Common in collection letters
            "Notice of",
            "Legal Notice"
        ]
        
        # Secondary IS indicators
        self.is_secondary = [
            "EXEMPTION CLAIM FORM",
            "exemption claim form",
            "File No.",
            "file no."
        ]
    
    def detect_document_type(self, pdf_path: str, max_pages_to_check: int = 5) -> Tuple[str, float]:
        """
        Detect document type by analyzing PDF content
        
        Args:
            pdf_path: Path to PDF file
            max_pages_to_check: Maximum pages to analyze (for performance)
            
        Returns:
            Tuple of (document_type, confidence_score)
            document_type: 'IS', 'LTD', or 'UNKNOWN'
            confidence_score: 0.0 to 1.0
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_check = min(max_pages_to_check, total_pages)
                
                is_score = 0.0
                ltd_score = 0.0
                
                for i in range(pages_to_check):
                    page_text = pdf.pages[i].extract_text() or ""
                    
                    # Check for Information Subpoena patterns
                    for pattern in self.is_patterns:
                        if pattern in page_text:
                            is_score += 1.0  # Strong indicator
                            logger.debug(f"Found IS pattern '{pattern}' on page {i+1}")
                    
                    # Check secondary IS patterns
                    for pattern in self.is_secondary:
                        if pattern in page_text:
                            is_score += 0.3  # Weaker indicator
                            logger.debug(f"Found IS secondary pattern '{pattern}' on page {i+1}")
                    
                    # Check for LTD patterns
                    for pattern in self.ltd_patterns:
                        if pattern in page_text:
                            ltd_score += 0.5
                            logger.debug(f"Found LTD pattern '{pattern}' on page {i+1}")
                
                # Normalize scores
                max_possible_is = pages_to_check * 1.0 + pages_to_check * 0.3 * len(self.is_secondary)
                max_possible_ltd = pages_to_check * 0.5 * len(self.ltd_patterns)
                
                if max_possible_is > 0:
                    is_confidence = min(is_score / max_possible_is, 1.0)
                else:
                    is_confidence = 0.0
                
                if max_possible_ltd > 0:
                    ltd_confidence = min(ltd_score / max_possible_ltd, 1.0)
                else:
                    ltd_confidence = 0.0
                
                # Decision logic
                if is_score > 0.0:  # Any IS pattern found
                    return "IS", is_confidence
                elif ltd_score > 0.0:  # Any LTD pattern found
                    return "LTD", ltd_confidence
                else:
                    return "UNKNOWN", 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing PDF {pdf_path}: {e}")
            return "UNKNOWN", 0.0
    
    def quick_detect(self, pdf_path: str) -> str:
        """
        Quick detection - just returns document type
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            'IS', 'LTD', or 'UNKNOWN'
        """
        doc_type, _ = self.detect_document_type(pdf_path, max_pages_to_check=3)
        return doc_type
    
    def analyze_first_page(self, pdf_path: str) -> dict:
        """
        Analyze just the first page for quick detection
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with analysis results
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return {"type": "UNKNOWN", "reason": "No pages found"}
                
                first_page = pdf.pages[0].extract_text() or ""
                
                # Check for definitive IS marker
                for pattern in self.is_patterns:
                    if pattern in first_page:
                        return {
                            "type": "IS",
                            "reason": f"Found '{pattern}' on first page",
                            "confidence": 0.95
                        }
                
                # Check for LTD patterns
                ltd_matches = []
                for pattern in self.ltd_patterns:
                    if pattern in first_page:
                        ltd_matches.append(pattern)
                
                if ltd_matches:
                    return {
                        "type": "LTD", 
                        "reason": f"Found LTD patterns: {ltd_matches}",
                        "confidence": len(ltd_matches) * 0.2
                    }
                
                return {
                    "type": "UNKNOWN",
                    "reason": "No recognizable patterns found",
                    "confidence": 0.0
                }
                
        except Exception as e:
            return {
                "type": "UNKNOWN",
                "reason": f"Error: {e}",
                "confidence": 0.0
            }


def main():
    """Test the detector"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 document_detector.py <pdf_file>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    detector = DocumentTypeDetector()
    
    print(f"Analyzing: {pdf_file}")
    
    # Quick detection
    quick_result = detector.quick_detect(pdf_file)
    print(f"Quick Detection: {quick_result}")
    
    # Detailed detection
    doc_type, confidence = detector.detect_document_type(pdf_file)
    print(f"Detailed Detection: {doc_type} (confidence: {confidence:.2f})")
    
    # First page analysis
    first_page = detector.analyze_first_page(pdf_file)
    print(f"First Page Analysis: {first_page}")


if __name__ == "__main__":
    main()
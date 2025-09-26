#!/usr/bin/env python3
"""
Enhanced PDF Splitter for Virtual Mailroom
Optimized for NVIDIA RTX 6000 Ada 96GB GPU
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse

from PyPDF2 import PdfReader, PdfWriter
import pdfplumber

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PDFSplitter:
    """PDF Splitter with pattern-based extraction"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_files = []
        
        self.file_patterns = [
            r'Our File Number:\s*([A-Z0-9]{6,8})',  # Allow any mix of letters/digits
            r'File Number:\s*([A-Z0-9]{6,8})',
            r'File No[.:]?\s*([A-Z0-9]{6,8})',  # Added "File No." pattern
            r'File #:\s*([A-Z0-9]{6,8})',
            r'Case Number:\s*([A-Z0-9]{6,8})',
            r'Case No[.:]?\s*([A-Z0-9]{6,8})',
            r'Matter #:\s*([A-Z0-9]{6,8})'
        ]
        
        self.debtor_patterns = [
            r'To:\s*([^\n]+?)(?:\n|$)',
            r'Debtor:\s*([^\n]+?)(?:\n|$)',
            r'Re:\s*([^\n]+?)(?:\n|$)',
            r'Defendant:\s*([^\n]+?)(?:\n|$)'
        ]
        
        self.address_patterns = [
            r'(?:To:.*?\n)([^\n]+(?:\n[^\n]+){0,3})',
            r'(\d+\s+[^\n]+(?:\n[^\n]+){0,2})'
        ]
    
    def extract_file_number(self, text: str) -> Optional[str]:
        """Extract file number from text"""
        for pattern in self.file_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                file_number = match.group(1).strip().upper()
                file_number = re.sub(r'[^A-Z0-9]', '', file_number)

                # Apply smart OCR correction: if starts with "1" and is 8 chars,
                # likely should be "L" (common OCR error)
                if len(file_number) == 8 and file_number[0] == '1':
                    # Only correct if rest are digits (L + 7 digits pattern)
                    if file_number[1:].isdigit():
                        file_number = 'L' + file_number[1:]

                if len(file_number) <= 8:
                    return file_number
        return None
    
    def extract_debtor_name(self, text: str) -> Optional[str]:
        """Extract debtor name from text"""
        for pattern in self.debtor_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\s+', ' ', name)
                name = re.sub(r'[^\w\s,.-]', '', name)
                if len(name) > 2 and len(name) < 100:
                    return name
        return None
    
    def extract_address(self, text: str) -> Optional[str]:
        """Extract address from text"""
        for pattern in self.address_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                address = match.group(1).strip()
                address = re.sub(r'\s+', ' ', address)
                if len(address) > 5 and len(address) < 200:
                    return address
        return None
    
    def detect_document_type(self, text: str, filename: Optional[str] = None) -> str:
        """Detect document type from content and filename"""
        text_lower = text.lower()

        # Check filename patterns first for specific types
        if filename:
            filename_upper = filename.upper()
            if 'REG_F_SCAN' in filename_upper:
                return "LTD"

        # Check for Information Subpoena first (most specific)
        if 'information subpoena with restraining notice' in text_lower:
            return "IS"
        elif any(term in text_lower for term in ['registration', 'register', 'filing']):
            return "REGF"
        elif any(term in text_lower for term in ['affidavit', 'sworn', 'notarized']):
            return "AFF"
        elif any(term in text_lower for term in ['initial', 'complaint', 'petition']):
            return "ICD"
        elif any(term in text_lower for term in ['notice', 'notification']):
            return "NOTICE"
        elif any(term in text_lower for term in ['summons', 'subpoena']):
            return "SUMMONS"
        elif any(term in text_lower for term in ['motion', 'brief']):
            return "MOTION"
        else:
            return "UNKNOWN"
    
    def detect_jurisdiction(self, text: str) -> Optional[str]:
        """Detect NY or NJ jurisdiction"""
        text_lower = text.lower()
        
        ny_indicators = ['new york', 'ny ', 'n.y.', 'state of new york', 'county of']
        nj_indicators = ['new jersey', 'nj ', 'n.j.', 'state of new jersey', 'superior court']
        
        ny_score = sum(1 for indicator in ny_indicators if indicator in text_lower)
        nj_score = sum(1 for indicator in nj_indicators if indicator in text_lower)
        
        if ny_score > nj_score:
            return "NY"
        elif nj_score > ny_score:
            return "NJ"
        return None
    
    def find_document_boundaries(self, pages_text: List[str]) -> List[Tuple[int, int]]:
        """Find document boundaries based on file number patterns"""
        boundaries = []
        current_start = None
        
        for i, text in enumerate(pages_text):
            file_num = self.extract_file_number(text)
            
            if file_num:
                if current_start is not None:
                    boundaries.append((current_start, i - 1))
                current_start = i
        
        if current_start is not None:
            boundaries.append((current_start, len(pages_text) - 1))
        
        if not boundaries and pages_text:
            return [(0, len(pages_text) - 1)]
        
        return boundaries
    
    def extract_is_file_number(self, pages_text: List[str]) -> Optional[str]:
        """Extract IS file number from page 2 specifically

        IS documents have format on page 2:
        Attorney for Judgment Creditor
        File No. L1800998
        """
        if len(pages_text) < 2:
            return None

        page2_text = pages_text[1]  # Page 2 (0-indexed)

        # Look for file number after "File No."
        patterns = [
            r'File\s*No[.:]\s*([A-Z0-9]{6,8})',
            r'Attorney.*\n.*File\s*No[.:]\s*([A-Z0-9]{6,8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, page2_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                file_number = match.group(1).strip().upper()
                # Apply OCR correction for first character
                if len(file_number) == 8 and file_number[0] == '1':
                    if file_number[1:].isdigit():
                        file_number = 'L' + file_number[1:]
                return file_number
        return None

    def split_pdf(self, input_pdf_path: str, doc_type: Optional[str] = None,
                  pages_per_doc: Optional[int] = None, auto_detect: bool = True):
        """Split PDF into individual documents"""
        input_path = Path(input_pdf_path)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_pdf_path}")
            return []
        
        try:
            reader = PdfReader(input_pdf_path)
            total_pages = len(reader.pages)
            logger.info(f"Processing: {input_path.name} ({total_pages} pages)")
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            return []
        
        pages_text = []
        with pdfplumber.open(input_pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
        
        # Special handling for IS documents - always use fixed 7-page boundaries
        if doc_type == "IS":
            pages_per_doc = 7
            boundaries = [(i, min(i + pages_per_doc - 1, total_pages - 1))
                         for i in range(0, total_pages, pages_per_doc)]
            logger.info(f"IS document: using fixed {pages_per_doc}-page boundaries, found {len(boundaries)} document(s)")
        elif auto_detect and not pages_per_doc:
            boundaries = self.find_document_boundaries(pages_text)
            logger.info(f"Auto-detected {len(boundaries)} document(s)")
        else:
            pages_per_doc = pages_per_doc or 1
            boundaries = [(i, min(i + pages_per_doc - 1, total_pages - 1))
                         for i in range(0, total_pages, pages_per_doc)]
        
        for doc_idx, (start_page, end_page) in enumerate(boundaries):
            first_page_text = pages_text[start_page] if start_page < len(pages_text) else ""
            all_pages_text = " ".join(pages_text[start_page:end_page+1])

            # For IS documents, extract file number from page 2
            if doc_type == "IS":
                # Get pages for this document boundary
                doc_pages = pages_text[start_page:end_page+1]
                file_number = self.extract_is_file_number(doc_pages)
                # If not found on page 2, try standard extraction on first page
                if not file_number:
                    file_number = self.extract_file_number(first_page_text)
            else:
                file_number = self.extract_file_number(first_page_text)

            debtor_name = self.extract_debtor_name(first_page_text)
            address = self.extract_address(first_page_text)
            
            if doc_type:
                document_type = doc_type
            elif auto_detect:
                document_type = self.detect_document_type(all_pages_text, input_path.name)
            else:
                document_type = "REGF"
            
            jurisdiction = self.detect_jurisdiction(all_pages_text)
            
            if not file_number:
                file_number = f"UNKNOWN_{doc_idx+1:03d}"
            
            output_filename = f"{document_type}_{file_number}.pdf"
            output_path = self.output_dir / output_filename
            
            writer = PdfWriter()
            for page_num in range(start_page, end_page + 1):
                if page_num < len(reader.pages):
                    writer.add_page(reader.pages[page_num])
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            doc_info = {
                'file_number': file_number,
                'debtor_name': debtor_name,
                'address': address,
                'document_type': document_type,
                'jurisdiction': jurisdiction,
                'output_file': output_filename,
                'pages': f"{start_page + 1}-{end_page + 1}",
                'page_count': end_page - start_page + 1,
                'timestamp': datetime.now().isoformat()
            }
            
            self.processed_files.append(doc_info)
            
            logger.info(f"Created: {output_filename}")
            logger.info(f"  File Number: {file_number}")
            logger.info(f"  Debtor: {debtor_name or 'Not found'}")
            logger.info(f"  Type: {document_type}")
            logger.info(f"  Jurisdiction: {jurisdiction or 'Unknown'}")
            logger.info(f"  Pages: {doc_info['pages']}")
        
        self.save_manifest()
        self.print_summary()
        
        return self.processed_files
    
    def save_manifest(self):
        """Save processing manifest to JSON"""
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump({
                'processed_at': datetime.now().isoformat(),
                'total_documents': len(self.processed_files),
                'documents': self.processed_files
            }, f, indent=2)
        logger.info(f"Manifest saved: {manifest_path}")
    
    def print_summary(self):
        """Print processing summary"""
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Total documents: {len(self.processed_files)}")
        print(f"Output directory: {self.output_dir}")
        
        doc_types = {}
        jurisdictions = {}
        
        for doc in self.processed_files:
            doc_type = doc['document_type']
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            jurisdiction = doc.get('jurisdiction', 'Unknown')
            jurisdictions[jurisdiction] = jurisdictions.get(jurisdiction, 0) + 1
        
        print("\nDocument Types:")
        for doc_type, count in sorted(doc_types.items()):
            print(f"  {doc_type}: {count}")
        
        print("\nJurisdictions:")
        for jurisdiction, count in sorted(jurisdictions.items(), key=lambda x: x[0] or 'ZZZ_Unknown'):
            print(f"  {jurisdiction or 'Unknown'}: {count}")
        
        print("\nProcessed Files:")
        for idx, doc in enumerate(self.processed_files, 1):
            print(f"\n{idx}. {doc['output_file']}")
            print(f"   File Number: {doc['file_number']}")
            if doc['debtor_name']:
                print(f"   Debtor: {doc['debtor_name']}")
            print(f"   Pages: {doc['pages']} ({doc['page_count']} page{'s' if doc['page_count'] > 1 else ''})")


def main():
    parser = argparse.ArgumentParser(
        description='Split multi-page PDFs into individual documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.pdf                     # Auto-detect and split
  %(prog)s input.pdf -p 1                # NJ format (1 page per doc)
  %(prog)s input.pdf -p 2                # NY format (2 pages per doc)
  %(prog)s input.pdf -t REGF              # Force document type
  %(prog)s input.pdf -o custom_output     # Custom output directory
        """
    )
    
    parser.add_argument('input_pdf', help='Path to input PDF file')
    parser.add_argument('-o', '--output', default='output', 
                       help='Output directory (default: output)')
    parser.add_argument('-t', '--type', 
                       choices=['LTD', 'IS', 'PI'],
                       help='Force document type')
    parser.add_argument('-p', '--pages', type=int,
                       help='Pages per document (1 for NJ, 2 for NY)')
    parser.add_argument('--no-auto', action='store_true',
                       help='Disable auto-detection of document boundaries')
    
    args = parser.parse_args()
    
    splitter = PDFSplitter(output_dir=args.output)
    splitter.split_pdf(
        args.input_pdf,
        doc_type=args.type,
        pages_per_doc=args.pages,
        auto_detect=not args.no_auto
    )


if __name__ == "__main__":
    main()
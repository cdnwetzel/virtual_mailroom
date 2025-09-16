#!/usr/bin/env python3
"""
Information Subpoena with Restraining Notice Processor
Specialized handler for IS documents with variable page lengths
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
import PyPDF2
import fitz  # PyMuPDF for OCR
from PIL import Image
import pytesseract
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InfoSubProcessor:
    """Processor for Information Subpoena with Restraining Notice documents"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_documents = []
        
        # Document boundary markers (flexible patterns to handle line breaks and OCR variations)
        self.start_markers = [
            "INFORMATION SUBPOENA WITH RESTRAINING NOTICE",
            "information subpoena with restraining notice",
            "INFORMATION SUBPOENA WITH",  # Partial match for line break cases
            "information subpoena with"
        ]
        
        # File number patterns for IS documents (FIRM FILE NUMBERS ONLY - NOT INDEX NUMBERS)
        # Only match actual firm file numbers, not court case index numbers
        # Enhanced to include letter-prefixed patterns found in analysis
        self.file_patterns = [
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
        
        # Additional document types that are part of the same subpoena
        self.continuation_markers = [
            "EXEMPTION CLAIM FORM",
            "exemption claim form"
        ]
    
    def extract_file_number(self, text: str) -> Optional[str]:
        """
        Extract file number from text (typically found on second page)
        Returns File No. if found, otherwise Index No.

        Args:
            text: Text content to search

        Returns:
            File number or None if not found
        """
        # First try to find File No. - proper 6-8 digit file numbers
        file_patterns = [
            r'Firm\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',  # Firm File No
            r'File\s+No[.:]?\s*([A-Z]?\d{6,8})',  # File No
            r'Our\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',  # Our File No
            r'Attorney\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',  # Attorney File No
            r'Client\s+File\s+No[.:]?\s*([A-Z]?\d{6,8})',  # Client File No
        ]

        for pattern in file_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                file_number = match.group(1).strip().upper()
                file_number = re.sub(r'[^A-Z0-9]', '', file_number)
                file_number = self._apply_ocr_corrections(file_number)
                if len(file_number) >= 6:  # Proper file number length requirement
                    return file_number

        # Do NOT fall back to Index numbers - only return actual firm file numbers
        # If no firm file number found, return None (document should be marked incomplete)
        return None

    def extract_index_number(self, text: str) -> Optional[str]:
        """
        Extract Index number to track document boundaries

        Args:
            text: Text content to search

        Returns:
            Index number or None if not found
        """
        patterns = [
            r'Index\s+No[.]?\s*([A-Z0-9\-/]+)',
            r'Case\s+No[.]?\s*([A-Z0-9\-/]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                index_no = match.group(1).strip().upper()
                index_no = re.sub(r'[^A-Z0-9\-/]', '', index_no)
                if len(index_no) >= 6:
                    return index_no
        return None

    def _apply_ocr_corrections(self, file_number: str) -> str:
        """
        Apply common OCR corrections for file numbers

        Args:
            file_number: Raw file number from OCR

        Returns:
            Corrected file number
        """
        if not file_number:
            return file_number

        # Common OCR corrections for IS file numbers
        corrections = {
            r'^32(\d{6})$': r'J2\1',    # J2 misread as 32
            r'^3(\d{7})$': r'J\1',       # J misread as 3
            r'^6(\d{7})$': r'G\1',       # G misread as 6
            r'^0(\d{7})$': r'G\1',       # G misread as 0
            r'^1(\d{7})$': r'L\1',       # L misread as 1
            r'^11(\d{6})$': r'L1\1',    # L1 misread as 11
            r'^12(\d{6})$': r'L2\1',    # L2 misread as 12
            r'^I(\d{7})$': r'L\1',       # L misread as I
            r'^L(\d{6})$': r'L\g<1>0',  # Add missing 0 if too short
        }

        corrected = file_number
        for pattern, replacement in corrections.items():
            if re.match(pattern, file_number):
                corrected = re.sub(pattern, replacement, file_number)
                if corrected != file_number:
                    logger.info(f"OCR correction: {file_number} -> {corrected}")
                break

        return corrected
    
    def is_document_start(self, text: str) -> bool:
        """
        Check if page contains document start marker
        
        Args:
            text: Page text content
            
        Returns:
            True if page starts a new document
        """
        text_clean = text.strip().upper()
        for marker in self.start_markers:
            if marker.upper() in text_clean:
                return True
        return False
    
    def is_blank_page(self, text: str) -> bool:
        """
        Check if page is blank or near-blank
        
        Args:
            text: Page text content
            
        Returns:
            True if page should be considered blank
        """
        # Remove whitespace and count meaningful characters
        clean_text = re.sub(r'\s+', '', text).strip()
        
        # Consider page blank if very few characters
        if len(clean_text) < 10:
            return True
        
        # Check for common "blank" page indicators
        blank_indicators = [
            'this page intentionally left blank',
            'blank page',
            '[blank]'
        ]
        
        text_lower = text.lower()
        for indicator in blank_indicators:
            if indicator in text_lower:
                return True
        
        return False
    
    def is_continuation_page(self, text: str) -> bool:
        """
        Check if page is part of current document (like exemption claim form)

        Args:
            text: Page text content

        Returns:
            True if page continues current document
        """
        text_upper = text.upper()
        for marker in self.continuation_markers:
            if marker.upper() in text_upper:
                return True
        return False

    def _extract_text_with_ocr(self, pdf_path: str, page_num: int, quick_mode: bool = False) -> str:
        """
        Extract text from a page using OCR

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            quick_mode: If True, only OCR top portion of page for faster processing

        Returns:
            Extracted text from OCR
        """
        try:
            doc = fitz.open(pdf_path)
            if page_num >= len(doc):
                return ""

            page = doc[page_num]

            # Get page dimensions
            rect = page.rect

            # In quick mode, only scan top 30% of page for faster boundary detection
            if quick_mode:
                clip_rect = fitz.Rect(0, 0, rect.width, rect.height * 0.3)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), clip=clip_rect)
            else:
                # Full page at reasonable resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            # Convert to PIL Image
            img_data = pix.tobytes("png")

            # Create temp file for OCR
            temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_img.write(img_data)
            temp_img.close()

            # Perform OCR
            text = pytesseract.image_to_string(Image.open(temp_img.name))

            # Clean up temp file
            os.unlink(temp_img.name)
            doc.close()

            return text

        except Exception as e:
            logger.error(f"OCR extraction failed for page {page_num}: {e}")
            return ""

    def find_document_boundaries(self, pdf_path: str) -> List[Tuple[int, int, str]]:
        """
        Find document boundaries in PDF with smart OCR for scanned documents

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of tuples: (start_page, end_page, file_number)
        """
        boundaries = []
        pages_text = []

        # First, try quick text extraction to detect if it's scanned
        is_scanned = False
        try:
            reader = PyPDF2.PdfReader(pdf_path)
            num_pages = len(reader.pages)

            # Sample a few pages to check if scanned
            sample_pages = [0, min(4, num_pages-1), min(10, num_pages-1)]
            empty_count = 0

            for page_idx in sample_pages:
                if page_idx < num_pages:
                    page = reader.pages[page_idx]
                    text = page.extract_text() or ""
                    if len(text.strip()) < 50:  # Very little text
                        empty_count += 1

            # If most sample pages are empty, it's likely scanned
            is_scanned = empty_count >= len(sample_pages) - 1

            if is_scanned:
                logger.info(f"Detected scanned document, using OCR strategy for {num_pages} pages")
                # For scanned docs, scan more frequently for IS documents
                # IS documents are typically 7 pages each, scan strategically
                for page_num in range(num_pages):
                    # OCR first 3 pages and every 3rd page for better boundary detection
                    # Also scan signature pages (7, 14, 21, 28, etc.)
                    if page_num < 3 or page_num % 3 == 0 or (page_num + 1) % 7 == 0:
                        logger.debug(f"OCR scanning page {page_num + 1} (quick mode)")
                        text = self._extract_text_with_ocr(pdf_path, page_num, quick_mode=True)
                    else:
                        text = ""  # Will be filled in later if needed
                    pages_text.append(text)
            else:
                # Not scanned, use PyPDF2 for all pages
                for page in reader.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)

        except Exception as e:
            logger.error(f"Error in boundary detection: {e}")
            # Fallback to PyPDF2
            try:
                reader = PyPDF2.PdfReader(pdf_path)
                for page in reader.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)
            except:
                return boundaries
        
        if not pages_text:
            logger.warning(f"No text found in PDF: {pdf_path}")
            return boundaries
        
        current_start = None
        current_file_number = None
        current_index_number = None

        for page_num, text in enumerate(pages_text):
            # Skip blank pages
            if self.is_blank_page(text):
                logger.debug(f"Skipping blank page {page_num + 1}")
                continue

            # For scanned docs with empty text, do full OCR if needed
            if is_scanned and not text and current_start is not None:
                # We're in a document, need to check this page
                text = self._extract_text_with_ocr(pdf_path, page_num, quick_mode=False)
                pages_text[page_num] = text

            # Extract Index number from this page
            page_index = self.extract_index_number(text)

            # Check if Index number changed (indicates new document)
            if page_index and page_index != current_index_number and current_start is not None:
                # Index changed, this is a new document
                logger.info(f"Index number changed from {current_index_number} to {page_index} at page {page_num + 1}")
                # Close current document
                boundaries.append((current_start, page_num - 1, current_file_number, current_index_number))
                # Start new document
                current_start = page_num
                current_file_number = None
                current_index_number = page_index
                logger.info(f"Found new subpoena starting at page {page_num + 1} (Index: {page_index})")

            # Check if this page starts a new document (by marker)
            elif self.is_document_start(text):
                # If we have a current document, close it
                if current_start is not None:
                    boundaries.append((current_start, page_num - 1, current_file_number, current_index_number))

                # Start new document
                current_start = page_num
                current_file_number = None
                current_index_number = page_index
                logger.info(f"Found new subpoena starting at page {page_num + 1}")

                # For scanned docs, OCR the next page (page 2) for file number
                if is_scanned and page_num + 1 < len(pages_text):
                    logger.debug(f"OCR scanning page {page_num + 2} for file number")
                    next_text = self._extract_text_with_ocr(pdf_path, page_num + 1, quick_mode=False)
                    pages_text[page_num + 1] = next_text
                    file_number = self.extract_file_number(next_text)
                    if file_number:
                        current_file_number = file_number
                        logger.info(f"Found file number via OCR: {file_number}")

            # Look for file number on current page if we're in a document
            elif current_start is not None and current_file_number is None:
                # Check current page for file number
                if not text and is_scanned:
                    # Need to OCR this page for file number
                    logger.debug(f"OCR scanning page {page_num + 1} for file number")
                    text = self._extract_text_with_ocr(pdf_path, page_num, quick_mode=False)
                    pages_text[page_num] = text

                file_number = self.extract_file_number(text)
                if file_number:
                    current_file_number = file_number
                    logger.info(f"Found file number on page {page_num + 1}: {file_number}")

        # Close the last document
        if current_start is not None:
            boundaries.append((current_start, len(pages_text) - 1, current_file_number, current_index_number))

        # After processing all pages, scan all documents for missing file numbers
        logger.info("Performing comprehensive file number scan across all pages...")
        for i, (start, end, file_num, index_num) in enumerate(boundaries):
            if file_num is None:
                logger.info(f"Scanning all pages of document {i+1} (pages {start+1}-{end+1}) for file number")
                for scan_page in range(start, end + 1):
                    # Get or extract text for this page
                    scan_text = pages_text[scan_page] if scan_page < len(pages_text) and pages_text[scan_page] else ""

                    # If no text and this is a scanned doc, OCR this page
                    if not scan_text and is_scanned and scan_page < len(pages_text):
                        logger.debug(f"OCR scanning page {scan_page + 1} for comprehensive file number search")
                        scan_text = self._extract_text_with_ocr(pdf_path, scan_page, quick_mode=False)
                        pages_text[scan_page] = scan_text

                    # Check for file number in this page
                    found_file_number = self.extract_file_number(scan_text)
                    if found_file_number:
                        boundaries[i] = (start, end, found_file_number, index_num)
                        logger.info(f"Found file number on page {scan_page + 1}: {found_file_number}")
                        break
        
        # Filter out documents that are too short (likely errors)
        valid_boundaries = []
        for start, end, file_num, index_num in boundaries:
            non_blank_pages = []
            for i in range(start, end + 1):
                if not self.is_blank_page(pages_text[i]):
                    non_blank_pages.append(i)
            
            if len(non_blank_pages) >= 1:  # At least one non-blank page
                valid_boundaries.append((start, end, file_num, index_num))
            else:
                logger.warning(f"Skipping document with no content: pages {start+1}-{end+1}")
        
        return valid_boundaries
    
    def process_pdf(self, input_pdf_path: str) -> List[Dict]:
        """
        Process PDF and split into individual subpoena documents

        Args:
            input_pdf_path: Path to input PDF

        Returns:
            List of processed document info
        """
        input_path = Path(input_pdf_path)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_pdf_path}")
            return []

        try:
            reader = PdfReader(input_pdf_path)
            total_pages = len(reader.pages)
            logger.info(f"Processing {input_path.name}: {total_pages} pages")

            # Detect if document is scanned
            is_scanned = False
            sample_pages = [0, min(4, total_pages-1), min(10, total_pages-1)]
            empty_count = 0
            for page_idx in sample_pages:
                if page_idx < total_pages:
                    page = reader.pages[page_idx]
                    text = page.extract_text() or ""
                    if len(text.strip()) < 50:
                        empty_count += 1
            is_scanned = empty_count >= len(sample_pages) - 1

            if is_scanned:
                logger.info("Detected scanned document - skipping blank page detection")

        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return []
        
        # Find document boundaries
        boundaries = self.find_document_boundaries(input_pdf_path)
        
        if not boundaries:
            logger.warning("No subpoena documents found in PDF")
            return []
        
        logger.info(f"Found {len(boundaries)} subpoena document(s)")
        
        # Process each document
        results = []
        incomplete_docs = []  # Track documents without File No.

        for doc_idx, (start_page, end_page, file_number, index_number) in enumerate(boundaries):
            logger.info(f"Processing document {doc_idx + 1}: pages {start_page + 1}-{end_page + 1}")

            # Check if document is complete (has File No.)
            is_complete = file_number and not file_number.startswith('CV-') and not file_number.startswith('EF') and '-' not in file_number

            # Use file number or mark as incomplete
            if file_number and is_complete:
                # Sanitize file number for filename (replace / with _)
                safe_file_number = file_number.replace('/', '_').replace('\\', '_')
                output_filename = f"{safe_file_number}_IS.pdf"
                output_subdir = self.output_dir
            else:
                # Document is incomplete (missing signature page with File No.)
                output_subdir = self.output_dir / "incomplete"
                output_subdir.mkdir(parents=True, exist_ok=True)

                # Use Index number for tracking (already extracted during boundary detection)
                index_no = index_number
                if index_no:
                    # Sanitize Index No. for filename (replace / with _)
                    safe_index = index_no.replace('/', '_').replace('\\', '_')
                    output_filename = f"INCOMPLETE_{safe_index}_IS.pdf"
                else:
                    output_filename = f"INCOMPLETE_{doc_idx + 1:03d}_IS.pdf"

                # Track incomplete document info
                incomplete_info = {
                    'doc_number': doc_idx + 1,
                    'index_no': index_no or 'UNKNOWN',
                    'pages': f"{start_page + 1}-{end_page + 1}",
                    'page_count': end_page - start_page + 1,
                    'filename': output_filename
                }
                incomplete_docs.append(incomplete_info)

                logger.warning(f"Document {doc_idx + 1} appears incomplete - no File No. found")
                if index_no:
                    logger.warning(f"  Index No.: {index_no}")
                logger.warning(f"  Saved to incomplete folder for review")
            
            output_path = output_subdir / output_filename
            
            # Create new PDF with only non-blank pages
            writer = PdfWriter()
            pages_included = 0
            
            for page_num in range(start_page, end_page + 1):
                if page_num < len(reader.pages):
                    # For scanned documents, include all pages
                    # For text documents, check if blank
                    if is_scanned:
                        # Include all pages for scanned docs (blank detection unreliable)
                        writer.add_page(reader.pages[page_num])
                        pages_included += 1
                    else:
                        # Check if page is blank by extracting text
                        with pdfplumber.open(input_pdf_path) as pdf:
                            if page_num < len(pdf.pages):
                                page_text = pdf.pages[page_num].extract_text() or ""
                                if not self.is_blank_page(page_text):
                                    writer.add_page(reader.pages[page_num])
                                    pages_included += 1
                                else:
                                    logger.debug(f"Excluding blank page {page_num + 1}")
            
            # Only save if we have pages
            if pages_included > 0:
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                doc_info = {
                    'file_number': file_number or f"UNKNOWN_{doc_idx + 1:03d}",
                    'document_type': 'IS',
                    'output_file': output_filename,
                    'original_pages': f"{start_page + 1}-{end_page + 1}",
                    'pages_included': pages_included,
                    'processing_timestamp': datetime.now().isoformat(),
                    'source_file': input_path.name
                }
                
                results.append(doc_info)
                self.processed_documents.append(doc_info)
                
                logger.info(f"Created: {output_filename}")
                logger.info(f"  File Number: {file_number or 'Not found'}")
                logger.info(f"  Pages: {pages_included} (excluded blanks)")
            else:
                logger.warning(f"Document {doc_idx + 1} has no content pages, skipping")

        # Create incomplete documents log if any were found
        if incomplete_docs:
            self.create_incomplete_log(incomplete_docs)

        return results

    def create_incomplete_log(self, incomplete_docs: List[Dict]):
        """Create a log file for incomplete documents"""
        log_path = self.output_dir / "incomplete" / "incomplete_documents.txt"

        with open(log_path, 'w') as f:
            f.write("INCOMPLETE DOCUMENTS LOG\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total incomplete documents: {len(incomplete_docs)}\n")
            f.write("=" * 60 + "\n\n")

            for doc in incomplete_docs:
                f.write(f"Document #{doc['doc_number']}\n")
                f.write(f"  Index No: {doc['index_no']}\n")
                f.write(f"  Pages: {doc['pages']} ({doc['page_count']} pages)\n")
                f.write(f"  Filename: {doc['filename']}\n")
                f.write(f"  Status: Missing File No. (likely missing signature page)\n")
                f.write("-" * 40 + "\n")

        logger.info(f"Created incomplete documents log: {log_path}")
    
    def generate_manifest(self) -> str:
        """Generate processing manifest"""
        manifest_path = self.output_dir / "infosub_manifest.json"
        
        import json
        manifest = {
            'processing_date': datetime.now().isoformat(),
            'document_type': 'Information Subpoena with Restraining Notice',
            'total_documents': len(self.processed_documents),
            'documents': self.processed_documents
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Manifest saved: {manifest_path}")
        return str(manifest_path)
    
    def print_summary(self):
        """Print processing summary"""
        print("\n" + "="*70)
        print("INFORMATION SUBPOENA PROCESSING SUMMARY")
        print("="*70)
        print(f"Total documents processed: {len(self.processed_documents)}")
        print(f"Output directory: {self.output_dir}")
        
        if self.processed_documents:
            print("\nProcessed Documents:")
            for idx, doc in enumerate(self.processed_documents, 1):
                print(f"\n{idx}. {doc['output_file']}")
                print(f"   File Number: {doc['file_number']}")
                print(f"   Original Pages: {doc['original_pages']}")
                print(f"   Pages Included: {doc['pages_included']} (blanks excluded)")


def main():
    """Main entry point for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Process Information Subpoena with Restraining Notice documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.pdf                    # Process single PDF
  %(prog)s input.pdf -o custom_output   # Custom output directory
  %(prog)s input.pdf --debug            # Enable debug logging
        """
    )
    
    parser.add_argument('input_pdf', help='Path to input PDF file')
    parser.add_argument('-o', '--output', default='output',
                       help='Output directory (default: output)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input file '{args.input_pdf}' not found")
        return 1
    
    processor = InfoSubProcessor(output_dir=args.output)
    results = processor.process_pdf(args.input_pdf)
    
    if results:
        processor.print_summary()
        processor.generate_manifest()
        print(f"\n✅ Successfully processed {len(results)} subpoena document(s)")
        return 0
    else:
        print("❌ No documents were processed")
        return 1


if __name__ == "__main__":
    exit(main())
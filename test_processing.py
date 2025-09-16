#!/usr/bin/env python3
"""
Test script to reproduce the processing error
"""

import traceback
from pathlib import Path
from document_detector import DocumentTypeDetector
from pdf_splitter import PDFSplitter
from infosub_processor import InfoSubProcessor

def test_document_processing(pdf_path, doc_type=None):
    """Test document processing to find the source of 'Unknown error'"""

    print(f"Testing: {pdf_path}")

    try:
        # Step 1: Auto-detect document type if needed
        actual_doc_type = doc_type
        if doc_type is None:  # Auto-Detect selected
            detector = DocumentTypeDetector()
            detected_type = detector.quick_detect(pdf_path)
            if detected_type == "IS":
                actual_doc_type = "IS"
            elif detected_type == "LTD":
                actual_doc_type = None  # Use standard splitter
            print(f"Auto-detected document type: {detected_type}")

        # Step 2: Choose processor based on document type
        output_dir = "test_output"
        Path(output_dir).mkdir(exist_ok=True)

        if actual_doc_type == "IS":
            # Use InfoSub processor for Information Subpoenas
            print("Using InfoSub processor...")
            processor = InfoSubProcessor(output_dir=output_dir)
            results = processor.process_pdf(pdf_path)
        else:
            # Use standard PDF splitter for LTD and other types
            print("Using PDF splitter...")
            splitter = PDFSplitter(output_dir=output_dir)
            results = splitter.split_pdf(
                pdf_path,
                doc_type=actual_doc_type,
                pages_per_doc=None,
                auto_detect=True
            )

        print(f"✅ Processing successful! Generated {len(results)} documents")
        for result in results[:3]:  # Show first 3
            print(f"  - {result}")

        return results

    except Exception as e:
        print(f"❌ Processing failed: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test with IS document
    is_pdf = "/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom/data/temp/temp_20250916_123745_NY_INFO_SUBS_9.16.2025.pdf"
    print("=" * 50)
    print("Testing IS document processing:")
    test_document_processing(is_pdf)

    print("\n" + "=" * 50)
    print("Testing LTD document processing:")
    # Test with LTD document
    ltd_pdf = "/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom/data/input/20250909_135751/NJ NOTICE LETTERS_09.02.2025.pdf"
    test_document_processing(ltd_pdf)
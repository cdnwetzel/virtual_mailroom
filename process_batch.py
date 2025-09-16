#!/usr/bin/env python3
"""
Batch Processing Script for Virtual Mailroom
Processes all PDFs in input folder and creates zip output
"""

import os
import sys
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime
from document_detector import DocumentTypeDetector
from pdf_splitter import PDFSplitter
from infosub_processor import InfoSubProcessor

def process_batch(input_dir="input", output_dir="output", create_zip=True):
    """Process all PDFs in input directory"""

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Create directories
    input_path.mkdir(exist_ok=True)
    output_path.mkdir(exist_ok=True)

    # Find all PDF files
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in {input_path}")
        return

    print(f"📂 Found {len(pdf_files)} PDF file(s) to process")
    print(f"📤 Input: {input_path.absolute()}")
    print(f"📥 Output: {output_path.absolute()}")
    print("=" * 50)

    detector = DocumentTypeDetector()
    total_documents = 0
    processed_files = []

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")

        try:
            # Auto-detect document type
            doc_type = detector.quick_detect(str(pdf_file))
            print(f"   📋 Auto-detected: {doc_type}")

            # Choose processor based on document type
            if doc_type == "IS":
                # Use InfoSub processor for Information Subpoenas
                processor = InfoSubProcessor(output_dir=str(output_path))
                results = processor.process_pdf(str(pdf_file))
                print(f"   ✅ Created {len(results)} IS documents")
            else:
                # Use standard PDF splitter for LTD and other types
                splitter = PDFSplitter(output_dir=str(output_path))
                results = splitter.split_pdf(
                    str(pdf_file),
                    doc_type=None,  # Let auto-detection work
                    auto_detect=True
                )
                print(f"   ✅ Created {len(results)} documents")

            total_documents += len(results)
            processed_files.append({
                'source': pdf_file.name,
                'type': doc_type,
                'count': len(results)
            })

        except Exception as e:
            print(f"   ❌ Error processing {pdf_file.name}: {e}")

    print("\n" + "=" * 50)
    print(f"📊 PROCESSING COMPLETE")
    print(f"   Total documents created: {total_documents}")
    print(f"   Success rate: {len(processed_files)}/{len(pdf_files)}")

    # Create summary
    print(f"\n📋 Summary by document type:")
    type_counts = {}
    for pf in processed_files:
        type_counts[pf['type']] = type_counts.get(pf['type'], 0) + pf['count']

    for doc_type, count in sorted(type_counts.items()):
        print(f"   {doc_type}: {count} documents")

    # Create zip file if requested
    if create_zip and total_documents > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"processed_documents_{timestamp}.zip"
        zip_path = output_path / zip_name

        print(f"\n📦 Creating zip file: {zip_name}")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all PDF files from output directory
            for pdf_file in output_path.glob("*.pdf"):
                zipf.write(pdf_file, pdf_file.name)
                print(f"   📄 Added: {pdf_file.name}")

            # Add manifest if it exists
            manifest_file = output_path / "manifest.json"
            if manifest_file.exists():
                zipf.write(manifest_file, "manifest.json")
                print(f"   📄 Added: manifest.json")

        print(f"✅ Zip created: {zip_path}")
        print(f"   Size: {zip_path.stat().st_size / 1024:.1f} KB")

    return total_documents, processed_files

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
Virtual Mailroom Batch Processor

Usage:
  python3 process_batch.py [input_dir] [output_dir]

Default:
  input_dir: ./input
  output_dir: ./output

The script will:
1. Auto-detect document types (IS, LTD, etc.)
2. Process each PDF accordingly
3. Create individual documents in output folder
4. Generate a timestamped zip file with all results

Examples:
  python3 process_batch.py
  python3 process_batch.py /path/to/pdfs /path/to/output
        """)
        return

    # Get directories from command line or use defaults
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "input"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    print("🚀 Virtual Mailroom Batch Processor")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        total_docs, processed = process_batch(input_dir, output_dir)

        if total_docs > 0:
            print(f"\n🎉 SUCCESS: Processed {total_docs} documents from {len(processed)} PDFs")
        else:
            print(f"\n⚠️  No documents were created")

    except KeyboardInterrupt:
        print(f"\n⏹️  Processing interrupted by user")
    except Exception as e:
        print(f"\n💥 Error during batch processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
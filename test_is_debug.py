#!/usr/bin/env python3
"""
Debug script for IS document processing
"""
import sys
import logging
import traceback
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('is_debug.log')
    ]
)

logger = logging.getLogger(__name__)

def test_is_processing(pdf_path):
    """Test IS document processing with detailed debugging"""
    try:
        logger.info("=" * 60)
        logger.info(f"Testing IS document: {pdf_path}")
        logger.info("=" * 60)

        # Import the processor
        logger.info("Importing InfoSubProcessor...")
        from infosub_processor import InfoSubProcessor

        # Create processor instance
        logger.info("Creating processor instance...")
        processor = InfoSubProcessor(output_dir="test_is_output")

        # Process the document
        logger.info("Starting document processing...")
        results = processor.process(pdf_path)

        if results:
            logger.info(f"✅ Successfully processed {len(results)} document(s)")
            for i, result in enumerate(results, 1):
                logger.info(f"  Document {i}: {result}")
        else:
            logger.warning("⚠️ No documents were processed (empty result)")

        return results

    except Exception as e:
        logger.error(f"❌ Processing failed with error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error("Full traceback:")
        traceback.print_exc()

        # Try to get more details about the error
        if hasattr(e, '__dict__'):
            logger.error(f"Error attributes: {e.__dict__}")

        return None

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_is_debug.py <pdf_path>")
        print("Example: python test_is_debug.py NY_INFO_SUBS_9.19.2025.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        logger.error(f"File not found: {pdf_path}")
        sys.exit(1)

    # Run the test
    results = test_is_processing(pdf_path)

    if results is None:
        logger.error("Test failed - check is_debug.log for details")
        sys.exit(1)
    else:
        logger.info("Test completed successfully")

if __name__ == "__main__":
    main()
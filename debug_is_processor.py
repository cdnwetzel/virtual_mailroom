#!/usr/bin/env python3
"""
Debug script to trace IS processor failure with detailed logging
"""
import sys
import os
import logging
import traceback
from pathlib import Path

# Set Python path to import from ChatPS_v2_ng
sys.path.insert(0, '/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom')

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('is_debug_detailed.log')
    ]
)

logger = logging.getLogger(__name__)

def test_is_processing():
    """Test IS processing with maximum debug info"""

    input_file = "/home/psadmin/ai/ChatPS_v2_ng/plugins/virtual_mailroom/data/temp/temp_20250919_144944_NY_INFO_SUBS_9.19.2025.pdf"

    try:
        logger.info("=" * 60)
        logger.info("Starting IS Processor Debug Test")
        logger.info("=" * 60)
        logger.info(f"Input file: {input_file}")

        # Check file exists
        if not Path(input_file).exists():
            logger.error(f"File not found: {input_file}")
            return False

        # Import the processor
        logger.info("Importing InfoSubProcessor from ChatPS_v2_ng...")
        try:
            from infosub_processor import InfoSubProcessor
            logger.info("✅ Import successful")
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            traceback.print_exc()
            return False

        # Create processor instance
        logger.info("Creating InfoSubProcessor instance...")
        try:
            processor = InfoSubProcessor(output_dir="debug_is_output")
            logger.info("✅ Processor instance created")
        except Exception as e:
            logger.error(f"❌ Failed to create processor: {e}")
            traceback.print_exc()
            return False

        # Process the PDF
        logger.info("Calling process_pdf method...")
        try:
            results = processor.process_pdf(input_file)
            logger.info(f"✅ process_pdf returned: {type(results)}")

            if results:
                logger.info(f"Successfully processed {len(results)} document(s)")
                for i, result in enumerate(results, 1):
                    logger.info(f"  Document {i}:")
                    for key, value in result.items():
                        logger.info(f"    {key}: {value}")
            else:
                logger.warning("⚠️ No documents were processed (empty result)")

            return True

        except Exception as e:
            logger.error(f"❌ process_pdf failed with exception: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error("Full traceback:")
            traceback.print_exc()

            # Try to get more details
            if hasattr(e, '__dict__'):
                logger.error(f"Exception attributes: {e.__dict__}")

            # Check if it's a tuple unpacking error
            if "too many values to unpack" in str(e) or "not enough values" in str(e):
                logger.error("This appears to be a tuple unpacking error - likely a mismatch in return values")

            return False

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    logger.info("Starting debug test...")

    success = test_is_processing()

    if success:
        logger.info("\n✅ Test completed successfully")
        logger.info("Check debug_is_output/ for processed files")
    else:
        logger.error("\n❌ Test failed - check is_debug_detailed.log for details")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
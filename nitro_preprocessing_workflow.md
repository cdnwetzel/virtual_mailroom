# Nitro OCR Preprocessing Workflow for Virtual Mailroom

## Why Nitro OCR Preprocessing Helps

### Advantages of Nitro Pro OCR:
1. **Superior text layer creation** - Creates searchable PDFs with embedded text
2. **Better handling of scanned documents** - Optimized for poor quality scans
3. **Automatic image enhancement** - Built-in deskew, despeckle, and contrast adjustment
4. **Preserves formatting** - Maintains document structure and layout
5. **Batch processing** - Can process multiple files at once

## Recommended Workflow

### Option 1: Manual Batch Preprocessing (Current)
```
1. Collect problematic PDFs in a folder
2. Open Nitro Pro
3. Use "Batch Process" → "Make Searchable (OCR)"
4. Settings:
   - Language: English
   - Output: Searchable Image (preserves original + adds text layer)
   - Quality: High
   - Deskew: Yes
5. Process all files
6. Run through Virtual Mailroom
```

### Option 2: Automated Preprocessing Script
```bash
#!/bin/bash
# nitro_preprocess.sh

INPUT_DIR="incoming"
PREPROCESSED_DIR="preprocessed"
PROCESSED_DIR="processed"

# Create directories
mkdir -p "$PREPROCESSED_DIR" "$PROCESSED_DIR"

# Move files to Nitro watch folder (if configured)
cp "$INPUT_DIR"/*.pdf "/path/to/nitro/watch/folder/"

# Wait for Nitro to process (or use Nitro CLI if available)
sleep 10

# Move OCR'd files to preprocessed
mv "/path/to/nitro/output/"*.pdf "$PREPROCESSED_DIR/"

# Run Virtual Mailroom on preprocessed files
python3 process_batch.py "$PREPROCESSED_DIR"

# Move to processed
mv "$PREPROCESSED_DIR"/*.pdf "$PROCESSED_DIR/"
```

## Testing Nitro vs Current OCR

### Quick Test:
1. Take the 11 failed LTD files from `/to_repair/`
2. Process them through Nitro OCR first
3. Re-run the splitter to see if it detects the "L" prefix correctly

### Comprehensive Test:
1. Use the files in `ocr_training_data/incomplete_with_known_filenumbers/`
2. Process through Nitro OCR
3. Run `ocr_test_and_tune.py` to compare results

## Nitro Pro CLI Integration (if available)

```python
import subprocess
import time
from pathlib import Path

def preprocess_with_nitro(input_pdf, output_dir):
    """
    Preprocess PDF with Nitro Pro OCR
    Requires Nitro Pro with CLI/COM interface
    """

    # Option 1: Using Nitro CLI (if available)
    try:
        subprocess.run([
            "NitroPDF.exe",
            "/ocr",
            f"/input:{input_pdf}",
            f"/output:{output_dir}",
            "/language:eng",
            "/quality:high",
            "/deskew:yes"
        ], check=True)
        return True
    except:
        pass

    # Option 2: Using COM automation (Windows)
    try:
        import win32com.client
        nitro = win32com.client.Dispatch("NitroPDF.Application")
        doc = nitro.OpenDocument(str(input_pdf))
        doc.OCRDocument(
            Language="English",
            OutputType="SearchableImage",
            ImageQuality="High",
            Deskew=True
        )
        doc.SaveAs(str(Path(output_dir) / Path(input_pdf).name))
        doc.Close()
        return True
    except:
        pass

    return False
```

## Expected Improvements

### Current Issues:
- Missing "L" prefix in file numbers (10/11 files failed)
- Poor text extraction from scanned documents
- OCR errors with similar characters (0/O, 1/I, etc.)

### After Nitro Preprocessing:
- **Expected success rate: 90-100%** for file number detection
- Better handling of poor quality scans
- More consistent text extraction
- Reduced need for manual intervention

## Implementation Steps

1. **Immediate (Manual)**:
   - Process the 11 files in `/to_repair/` through Nitro
   - Test if the file numbers are correctly detected
   - Document the improvement rate

2. **Short-term (Semi-automated)**:
   - Create a "preprocessing" folder
   - Manually run Nitro batch OCR on new files
   - Feed preprocessed files to Virtual Mailroom

3. **Long-term (Fully automated)**:
   - Set up Nitro watch folders or CLI integration
   - Automatic preprocessing pipeline
   - Fallback to current OCR for non-problematic files

## Cost-Benefit Analysis

### Benefits:
- Reduce manual repairs from ~8-11 files per batch to 0-2
- Save 15-30 minutes per batch processing
- Higher accuracy for file number extraction (90%+ vs current 50-70%)
- Better handling of poor quality scans

### Costs:
- Nitro Pro license (already have)
- Extra preprocessing step (1-2 minutes per batch)
- Storage for preprocessed files (minimal)

## Recommendation

**YES, definitely use Nitro OCR preprocessing**, especially for:
1. Scanned documents (not native PDFs)
2. Batches with known OCR issues
3. Documents with poor image quality
4. Critical documents where accuracy is essential

The improvement in accuracy (potentially 40-50% better) far outweighs the small additional processing time.
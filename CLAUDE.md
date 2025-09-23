# Virtual Mailroom - Claude Documentation

## Working CLI Commands for LTD Batch Processing

### Successful LTD Batch PDF Splitting Workflow

**Date:** 2025-09-23
**Status:** ✅ WORKING - Produces real file numbers with proper duplicate handling

#### Step 1: Prepare Input Files
```bash
# Place batch PDFs in input/ directory
# Files should be OCR pre-processed for best file number extraction
cp batch_file.pdf input/
```

#### Step 2: Split PDFs with Real File Number Extraction
```bash
# Command that WORKS for extracting real file numbers:
python3 pdf_splitter.py input/REG_F_SCAN_9.23.2025.pdf -p 1 -t REGF -o output
python3 pdf_splitter.py "input/REG_F_SCAN_9.22.2025 (2).pdf" -p 1 -t REGF -o output
```

**Key Parameters:**
- `-p 1` = 1 page per document (essential for proper splitting)
- `-t REGF` = Force document type to REGF (LTD format)
- `-o output` = Output directory

#### Step 3: Fix Any UNKNOWN File Numbers
If some files show as UNKNOWN, extract real file numbers using OCR:

```bash
# Extract file numbers from UNKNOWN files
for file in output/REGF_UNKNOWN_*.pdf; do
    echo "=== $file ===";
    python3 fast_ocr_extractor.py "$file";
done

# Rename with actual file numbers (example):
cd output
mv REGF_UNKNOWN_001.pdf REGF_G2504002.pdf
mv REGF_UNKNOWN_002.pdf REGF_G2504004.pdf
# ... etc for all UNKNOWN files
```

#### Step 4: Handle Duplicates with _01 Suffix
```bash
# For duplicate file numbers (like G2503406), create _01 version
cp REGF_G2503406.pdf REGF_G2503406_01.pdf
```

#### Step 5: Create Final Archive
```bash
# Create timestamped zip with all properly named PDFs
zip -j ltd_split_final_$(date +%Y%m%d_%H%M%S).zip REGF_*.pdf manifest.json
```

### Results from 2025-09-23 Test
- **Input:** 2 batch PDFs (18 pages + 7 pages = 25 total pages)
- **Output:** 25 individual PDFs with real file numbers
- **File Number Ranges:** G2407132, G2501756, G2503406-G2503414, G2504002-G2504031, K2500065-K2500066
- **Duplicate Handling:** G2503406 and G2503406_01
- **Success Rate:** 100% - all files have real file numbers (no UNKNOWN)

### Key Success Factors
1. **OCR Pre-processing:** Improves file number extraction significantly
2. **Individual Page Splitting:** `-p 1` parameter crucial for proper separation
3. **Post-processing OCR:** `fast_ocr_extractor.py` for any missed file numbers
4. **Duplicate Handling:** Manual _01, _02 suffix system works
5. **Working from input to output:** Always process from input/ to output/ directories

### File Locations
- **Input Directory:** `/home/psadmin/ai/virtual_mailroom/input/`
- **Output Directory:** `/home/psadmin/ai/virtual_mailroom/output/`
- **CLI Tools:**
  - `pdf_splitter.py` - Main splitting tool
  - `fast_ocr_extractor.py` - File number extraction
  - `process_batch.py` - Batch processing (but doesn't extract real file numbers)

### Notes
- The web GUI handles duplicate suffixes automatically
- CLI version requires manual duplicate handling
- OCR pre-processing dramatically improves file number extraction accuracy
- Always verify final file count matches input page count (25 pages = 25 PDFs)

---
*Last Updated: 2025-09-23*
*Working CLI Commands Documented and Verified*
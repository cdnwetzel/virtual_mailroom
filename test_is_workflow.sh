#!/bin/bash

echo "=== IS Document Processing Complete Workflow Test ==="
echo

# Step 1: Clean output directory
echo "Step 1: Cleaning output directory..."
rm -f output/IS_*.pdf output/manifest.json
echo "Done"
echo

# Step 2: Process the IS batch file
echo "Step 2: Processing NY_INFO_SUBS_9.26.2025.pdf as IS type..."
python3 pdf_splitter.py input/NY_INFO_SUBS_9.26.2025.pdf -t IS -o output
echo

# Step 3: Run post-processor for validation and corrections
echo "Step 3: Running IS post-processor..."
python3 is_postprocessor.py -d output
echo

# Step 4: Verify results
echo "Step 4: Verification Report:"
echo "----------------------------"
total_files=$(ls -1 output/IS_*.pdf 2>/dev/null | wc -l)
echo "Total IS documents created: $total_files"

unknown_files=$(ls -1 output/IS_UNKNOWN*.pdf 2>/dev/null | wc -l)
echo "UNKNOWN files remaining: $unknown_files"

if [ -f output/manifest.json ]; then
    echo "Manifest file: ✓ Created"
    total_in_manifest=$(python3 -c "import json; print(json.load(open('output/manifest.json'))['total_documents'])")
    echo "Documents in manifest: $total_in_manifest"
else
    echo "Manifest file: ✗ Missing"
fi

echo
echo "File numbers extracted:"
for file in output/IS_*.pdf; do
    basename=$(basename "$file")
    file_num=${basename#IS_}
    file_num=${file_num%.pdf}
    echo "  - $file_num"
done

echo
echo "=== Test Complete ==="

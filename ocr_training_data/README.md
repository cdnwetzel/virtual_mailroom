# OCR Training Data for Virtual Mailroom

## Purpose
This directory contains Information Subpoena documents where file numbers were manually identified but OCR pattern recognition failed to detect them automatically.

## Contents

### `incomplete_with_known_filenumbers/`
Contains 5 PDF files with manually confirmed file numbers for OCR training and validation:

| Original Filename | Known File Number | Pattern Type |
|-------------------|-------------------|--------------|
| INCOMPLETE_40651_07_IS.pdf | Y1301388 | Y-prefix, 8 digits |
| INCOMPLETE_629384_2024_IS.pdf | L2401724 | L-prefix, 7 digits |
| INCOMPLETE_701405_2025_IS.pdf | L2402234 | L-prefix, 7 digits |
| INCOMPLETE_710506_2024_IS.pdf | JM2210250 | JM-prefix, 7 digits |
| INCOMPLETE_EF20251433_IS.pdf | L2500212 | L-prefix, 7 digits |

## Training Objectives

1. **Pattern Recognition Improvement**: Train OCR to better detect:
   - Letter-prefixed file numbers (L, Y, JM)
   - Various digit lengths (7-8 digits)
   - Different text formatting in scanned documents

2. **Context Understanding**: Improve detection of:
   - "File No." labels
   - "Account Number:" alternative patterns
   - Various spacing and punctuation formats

3. **OCR Quality Enhancement**:
   - Address text extraction issues in scanned documents
   - Improve character recognition accuracy
   - Handle document quality variations

## Success Metrics
- Current enhanced patterns detect 1/6 files automatically (L2402446)
- Goal: Achieve 5/6 or 6/6 automatic detection rate
- Validate against these known ground truth file numbers

## Generated
Date: 2025-09-16
Virtual Mailroom Pattern Enhancement Project
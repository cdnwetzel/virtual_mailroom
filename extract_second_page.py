#!/usr/bin/env python3
"""Extract second page from an LTD document to use as template"""

from PyPDF2 import PdfReader, PdfWriter

# Extract second page from the test LTD file
reader = PdfReader("/home/psadmin/ai/virtual_mailroom/test_output/LTD_UNKNOWN_001.pdf")
if len(reader.pages) >= 2:
    writer = PdfWriter()
    writer.add_page(reader.pages[1])  # Second page (index 1)

    with open("/home/psadmin/ai/virtual_mailroom/LTD_second_page_template.pdf", "wb") as output:
        writer.write(output)
    print("✅ Extracted second page to LTD_second_page_template.pdf")
else:
    print("❌ Source file doesn't have a second page")
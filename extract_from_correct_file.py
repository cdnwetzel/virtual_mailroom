#!/usr/bin/env python3
"""Extract second page from the correct L2501396_LTD.PDF file"""

from PyPDF2 import PdfReader, PdfWriter

# Extract second page from the correct file that already has 2 pages
reader = PdfReader("/home/psadmin/ai/virtual_mailroom/to_repair/L2501396_LTD.PDF")
if len(reader.pages) >= 2:
    writer = PdfWriter()
    writer.add_page(reader.pages[1])  # Second page (index 1)

    with open("/home/psadmin/ai/virtual_mailroom/LTD_correct_second_page.pdf", "wb") as output:
        writer.write(output)
    print("✅ Extracted second page from L2501396_LTD.PDF to LTD_correct_second_page.pdf")
else:
    print("❌ Source file doesn't have a second page")
# Virtual Mailroom System

An intelligent document processing system that splits multi-page PDFs, extracts metadata, and routes documents using AI-powered analysis.

## Supported Document Types

### 1. Legal/Collection Documents (REGF, AFF, etc.)
- **Pattern**: "Our File Number: A1234567"
- **Naming**: `REGF_A1234567.pdf`
- **Pages**: Fixed (1 for NJ, 2 for NY) or auto-detect
- **Extraction**: File numbers, debtor names, addresses

### 2. Information Subpoena with Restraining Notice (IS)
- **Pattern**: "INFORMATION SUBPOENA WITH RESTRAINING NOTICE"
- **File Number**: "File No. A1234567" (typically on second page)
- **Naming**: `A1234567_IS.pdf`
- **Pages**: Variable length with boundary detection
- **Features**: 
  - Includes "EXEMPTION CLAIM FORM" as part of same document
  - Automatically removes blank pages
  - Splits at each new "INFORMATION SUBPOENA WITH RESTRAINING NOTICE"

## Features

### Core Capabilities
- **PDF Splitting**: Automatically split multi-page PDFs into individual documents
- **Metadata Extraction**: Extract file numbers, debtor names, addresses, and other key information
- **Document Classification**: Identify document types (REGF, IS, AFF, ICD, NOTICE, etc.)
- **Jurisdiction Detection**: Automatically detect NY vs NJ documents
- **Priority Routing**: Route documents to appropriate departments based on content
- **AI Enhancement**: Optional integration with ChatPS for advanced processing

### Processing Modes
1. **Simple Mode**: Pattern-based extraction using regex
2. **AI-Enhanced Mode**: Leverages ChatPS API for intelligent processing
3. **Hybrid Mode**: Uses patterns with AI fallback

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make startup script executable
chmod +x start_mailroom.sh
```

### Basic Usage

#### 1. Legal Documents (Standard PDF Splitting)
```bash
# Split a PDF with auto-detection
python3 pdf_splitter.py input.pdf

# NJ format (1 page per document)
python3 pdf_splitter.py input.pdf -p 1

# NY format (2 pages per document)  
python3 pdf_splitter.py input.pdf -p 2

# Force document type
python3 pdf_splitter.py input.pdf -t REGF
```

#### 2. Information Subpoenas
```bash
# Process Information Subpoena document
python3 infosub_processor.py input.pdf

# With custom output directory
python3 infosub_processor.py input.pdf -o custom_output

# Enable debug logging
python3 infosub_processor.py input.pdf --debug
```

#### 3. Interactive Menu
```bash
./start_mailroom.sh
```

#### 4. Web Dashboard
```bash
streamlit run mailroom_web.py --server.port 8510
```

## File Naming Conventions

### Legal Documents
- Format: `{DOCUMENT_TYPE}_{FILE_NUMBER}.pdf`
- Examples:
  - `REGF_A1234567.pdf` - Registration filing
  - `AFF_B9876543.pdf` - Affidavit
  - `ICD_12345678.pdf` - Initial case document

### Information Subpoenas
- Format: `{FILE_NUMBER}_IS.pdf`
- Examples:
  - `A1234567_IS.pdf`
  - `B9876543_IS.pdf`

## Pattern Recognition

### Legal Documents
- File Numbers: "Our File Number: A1234567"
- Debtor Names: "To: John Doe"
- Addresses: Multi-line address extraction

### Information Subpoenas
- Document Start: "INFORMATION SUBPOENA WITH RESTRAINING NOTICE"
- File Numbers: "File No. A1234567" (on second page)
- Continuation: "EXEMPTION CLAIM FORM"
- Blank Page Detection: Automatic removal

## ChatPS Integration

The system can integrate with your existing ChatPS infrastructure:

### Available Environments
- **Production**: Port 8501/443
- **Development**: Port 8502/444
- **NextGen (GPU)**: Port 8503/447 (Recommended)

### Testing Connection
```bash
python3 mailroom_chatps_integration.py --env nextgen --test
```

## Web Interface

Access the Streamlit dashboard at http://localhost:8510

### Features
- Drag-and-drop PDF upload
- Document type selection (Auto-Detect, REGF, IS, AFF, etc.)
- Processing progress indicators
- Dashboard with statistics
- Export results to CSV
- Batch processing

## As ChatPS Plugin

The Virtual Mailroom can run as a tab in ChatPS_ng:

```bash
# Run modular ChatPS with Virtual Mailroom tab
streamlit run /home/psadmin/ai/ChatPS_v2_ng/modules/chatps_modular_ui.py --server.port 8503
```

## Project Structure

```
virtual_mailroom/
├── pdf_splitter.py              # Legal document processor
├── infosub_processor.py         # Information Subpoena processor
├── virtual_mailroom_ai.py       # Standalone AI processing
├── mailroom_chatps_integration.py # ChatPS API integration
├── mailroom_plugin.py           # ChatPS plugin version
├── mailroom_web.py              # Streamlit web interface
├── test_pdf_splitter.py         # Test suite for legal docs
├── test_infosub.py              # Test suite for subpoenas
├── start_mailroom.sh            # Interactive launcher
├── plugin_config.json           # Plugin configuration
├── requirements.txt             # Python dependencies
└── output/                      # Default output directory
```

## Testing

### Legal Documents
```bash
python3 test_pdf_splitter.py
```

### Information Subpoenas
```bash
python3 test_infosub.py
```

### Full System
```bash
# Test plugin system (requires ChatPS_ng)
python3 /home/psadmin/ai/ChatPS_v2_ng/test_modular_system.py
```

## Configuration

### Document Types Supported
- **REGF**: Registration/Filing documents
- **IS**: Information Subpoena with Restraining Notice
- **AFF**: Affidavits
- **ICD**: Initial Case Documents
- **NOTICE**: Legal Notices
- **SUMMONS**: Court Summons
- **MOTION**: Legal Motions
- **JUDGMENT**: Court Judgments
- **OTHER**: Other document types

### Processing Options
- **Auto-detect boundaries**: Default enabled for legal docs
- **Variable length**: Default for Information Subpoenas
- **Blank page removal**: Automatic for IS documents
- **Pages per document**: Configurable for legal docs

## Batch Processing

Process multiple PDFs:
```bash
# Using shell script
./start_mailroom.sh
# Select option 4 for batch processing

# Manual batch for legal documents
for pdf in input/*.pdf; do
    python3 pdf_splitter.py "$pdf" -o output
done

# Manual batch for Information Subpoenas
for pdf in input/*.pdf; do
    python3 infosub_processor.py "$pdf" -o output
done
```

## Output Files

### Manifest Files
Each processing run creates manifest files:
- `manifest.json` - Legal document processing
- `infosub_manifest.json` - Information Subpoena processing

### CSV Export
Export results to CSV for analysis:
```bash
python3 mailroom_chatps_integration.py --csv
```

## Performance

- **Simple mode**: ~100-200 pages/second
- **AI-enhanced mode**: ~5-10 pages/second (depends on ChatPS)
- **GPU acceleration**: 20-45x faster with NextGen environment
- **Information Subpoenas**: Variable speed based on document complexity

## Troubleshooting

### Missing Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Pattern Not Matching
- Check file number format in `infosub_processor.py`
- Enable debug logging: `--debug`
- Review pattern extraction in test files

### ChatPS Connection Issues
```bash
# Test connectivity
python3 -c "import requests; print(requests.get('http://localhost:8503/health').status_code)"
```

## Advanced Usage

### Custom Patterns for Information Subpoenas
Edit patterns in `infosub_processor.py`:
```python
self.file_patterns = [
    r'File No[.:]?\s*([A-Z]?\d{7})',
    r'Your Custom Pattern Here',
]
```

### Custom Document Start Markers
```python
self.start_markers = [
    "INFORMATION SUBPOENA WITH RESTRAINING NOTICE",
    "Your Custom Start Marker",
]
```

## Examples

### Processing Mixed Document Types
The web interface and plugin automatically detect document types:

1. Upload mixed PDFs containing both legal documents and Information Subpoenas
2. Select "Auto-Detect" document type
3. System will:
   - Use `pdf_splitter.py` for legal documents (REGF, AFF, etc.)
   - Use `infosub_processor.py` for Information Subpoenas (IS)
   - Apply appropriate processing logic for each type

### Information Subpoena Processing Flow
1. **Detection**: Finds "INFORMATION SUBPOENA WITH RESTRAINING NOTICE"
2. **Boundary**: Continues until next subpoena or end of file
3. **Inclusion**: Includes "EXEMPTION CLAIM FORM" as part of same document
4. **File Number**: Extracts from second page: "File No. A1234567"
5. **Cleanup**: Removes blank pages automatically
6. **Output**: Creates `A1234567_IS.pdf`

## Support

For issues or questions:
- Check existing test output
- Review pattern matching logs
- Test with sample documents
- Check ChatPS connection status

## License

Part of the ChatPS ecosystem - internal use only

---
*Last Updated: 2025-01-08*
*Now supports dual document types: Legal Collections and Information Subpoenas*
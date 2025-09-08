"""
AI-Enhanced PDF Splitter using Local LLM
Designed for NVIDIA RTX 6000 Ada 96GB GPU
"""

import re
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# PDF processing
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber

# For local LLM approach
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    pipeline
)

class DocumentIntelligence:
    """AI-powered document analysis using local LLM"""
    
    def __init__(self, model_name: str = "meta-llama/Llama-3.2-3B-Instruct", use_gpu: bool = True):
        """
        Initialize local LLM for document processing.
        
        Recommended models for RTX 6000 96GB:
        - meta-llama/Llama-3.2-3B-Instruct (lightweight, fast)
        - mistralai/Mistral-7B-Instruct-v0.3 (balanced)
        - meta-llama/Meta-Llama-3.1-8B-Instruct (more capable)
        - NousResearch/Hermes-3-Llama-3.1-8B (good for extraction)
        """
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        
        if self.device == "cuda":
            print(f"Using GPU: {torch.cuda.get_device_name(0)}")
            print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        
        print(f"Loading model: {model_name}")
        
        # Load model with appropriate settings for your GPU
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,  # Use float16 for efficiency
            device_map="auto",  # Automatically use GPU
            load_in_8bit=False,  # Set to True if you want to save memory
            trust_remote_code=True
        )
        
        # Create pipeline for easy inference
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=self.device,
            max_new_tokens=256,
            temperature=0.1,  # Low temperature for consistent extraction
            do_sample=False
        )
    
    def extract_structured_data(self, text: str) -> Dict:
        """
        Use LLM to extract structured data from document text.
        """
        prompt = f"""Extract the following information from this document text. 
Return ONLY a JSON object with the exact structure shown, no additional text:

{{"file_number": "extracted file number or null",
  "debtor_name": "extracted debtor name or null", 
  "creditor_name": "extracted creditor name or null",
  "document_type": "REGF, AFF, ICD, or UNKNOWN",
  "case_type": "NJ or NY if determinable, else null"}}

Document text:
{text[:2000]}  # Limit context to avoid token limits

JSON Response:"""
        
        try:
            response = self.pipe(prompt)[0]['generated_text']
            # Extract JSON from response
            json_start = response.find('{', response.find('JSON Response:'))
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            print(f"LLM extraction error: {e}")
        
        return {}
    
    def classify_document(self, text: str) -> str:
        """
        Classify document type using LLM.
        """
        prompt = f"""Classify this legal document into one of these categories:
- REGF: Registration or filing documents
- AFF: Affidavits
- ICD: Initial case documents
- NOTICE: Legal notices
- OTHER: Other document types

Document excerpt:
{text[:1000]}

Classification (respond with just the category):"""
        
        try:
            response = self.pipe(prompt)[0]['generated_text']
            # Extract classification from response
            for doc_type in ['REGF', 'AFF', 'ICD', 'NOTICE', 'OTHER']:
                if doc_type in response.upper():
                    return doc_type
        except Exception as e:
            print(f"Classification error: {e}")
        
        return "UNKNOWN"
    
    def find_document_boundaries(self, pages_text: List[str]) -> List[Tuple[int, int]]:
        """
        Use LLM to identify where documents start and end in a multi-page PDF.
        Returns list of (start_page, end_page) tuples.
        """
        boundaries = []
        current_doc_start = 0
        
        for i in range(1, len(pages_text)):
            # Check if this page starts a new document
            prompt = f"""Does Page 2 appear to be the start of a NEW document, or a continuation of the document from Page 1?

Page 1 ending:
{pages_text[i-1][-500:]}

Page 2 beginning:
{pages_text[i][:500]}

Answer with just: NEW_DOCUMENT or CONTINUATION"""
            
            try:
                response = self.pipe(prompt)[0]['generated_text']
                if "NEW_DOCUMENT" in response.upper():
                    boundaries.append((current_doc_start, i-1))
                    current_doc_start = i
            except Exception as e:
                print(f"Boundary detection error: {e}")
        
        # Add final document
        boundaries.append((current_doc_start, len(pages_text)-1))
        return boundaries


class HybridPDFSplitter:
    """Hybrid approach: regex patterns with AI fallback"""
    
    def __init__(self, use_ai: bool = False, model_name: Optional[str] = None):
        self.use_ai = use_ai
        self.ai = None
        
        if use_ai:
            model = model_name or "meta-llama/Llama-3.2-3B-Instruct"
            self.ai = DocumentIntelligence(model)
    
    def extract_with_regex(self, text: str) -> Dict:
        """Traditional regex extraction (fast, reliable for consistent formats)"""
        result = {
            'file_number': None,
            'debtor_name': None,
            'document_type': 'REGF'  # Default
        }
        
        # File number patterns
        file_patterns = [
            r'Our File Number:\s*([A-Z]{1,2}\d{1,7}|\d{1,8})',
            r'File #:\s*([A-Z]{1,2}\d{1,7}|\d{1,8})',
            r'Case Number:\s*([A-Z]{1,2}\d{1,7}|\d{1,8})'
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['file_number'] = match.group(1).strip()
                break
        
        # Debtor name
        name_pattern = r'To:\s*([^\n]+?)(?:\n|$|(?=\s{2,}))'
        match = re.search(name_pattern, text, re.IGNORECASE)
        if match:
            result['debtor_name'] = re.sub(r'\s+', ' ', match.group(1).strip())
        
        return result
    
    def extract_data(self, text: str) -> Dict:
        """Extract data using regex first, fall back to AI if needed"""
        # Try regex first (fast)
        result = self.extract_with_regex(text)
        
        # If regex fails and AI is available, use it
        if self.use_ai and self.ai and not result['file_number']:
            print("  Using AI for extraction...")
            ai_result = self.ai.extract_structured_data(text)
            
            # Merge AI results with regex results
            for key in ['file_number', 'debtor_name', 'document_type']:
                if key in ai_result and ai_result[key] and not result.get(key):
                    result[key] = ai_result[key]
        
        return result
    
    def split_pdf(self, input_pdf_path: str, output_dir: str = "output", 
                  doc_type: Optional[str] = None, pages_per_doc: Optional[int] = None):
        """
        Split PDF with hybrid approach
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        try:
            reader = PdfReader(input_pdf_path)
            total_pages = len(reader.pages)
            print(f"Total pages in PDF: {total_pages}")
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return []
        
        processed_files = []
        
        # If using AI and no pages_per_doc specified, detect boundaries
        if self.use_ai and self.ai and pages_per_doc is None:
            print("Using AI to detect document boundaries...")
            pages_text = []
            for i in range(total_pages):
                with pdfplumber.open(input_pdf_path) as pdf:
                    pages_text.append(pdf.pages[i].extract_text() or "")
            
            boundaries = self.ai.find_document_boundaries(pages_text)
            print(f"Detected {len(boundaries)} documents")
        else:
            # Use fixed page count
            pages_per_doc = pages_per_doc or 1
            boundaries = [(i, min(i + pages_per_doc - 1, total_pages - 1)) 
                         for i in range(0, total_pages, pages_per_doc)]
        
        # Process each document
        for doc_idx, (start_page, end_page) in enumerate(boundaries):
            print(f"\nProcessing document {doc_idx + 1} (pages {start_page + 1}-{end_page + 1})")
            
            # Extract text from first page for metadata
            with pdfplumber.open(input_pdf_path) as pdf:
                text = pdf.pages[start_page].extract_text() or ""
            
            # Extract data
            data = self.extract_data(text)
            
            # Determine document type
            if doc_type:
                data['document_type'] = doc_type
            elif self.use_ai and self.ai and not data.get('document_type'):
                data['document_type'] = self.ai.classify_document(text)
            
            file_number = data.get('file_number', f"UNKNOWN_{doc_idx+1:03d}")
            document_type = data.get('document_type', 'UNKNOWN')
            
            # Create output filename
            output_filename = f"{document_type}_{file_number}.pdf"
            output_path = os.path.join(output_dir, output_filename)
            
            # Write PDF
            writer = PdfWriter()
            for page_num in range(start_page, end_page + 1):
                writer.add_page(reader.pages[page_num])
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            processed_files.append({
                'file_number': file_number,
                'debtor_name': data.get('debtor_name'),
                'document_type': document_type,
                'output_file': output_filename,
                'pages': f"{start_page + 1}-{end_page + 1}"
            })
            
            print(f"Created: {output_filename}")
            print(f"  File Number: {file_number}")
            print(f"  Debtor Name: {data.get('debtor_name', 'Not found')}")
            print(f"  Document Type: {document_type}")
        
        # Summary
        print("\n" + "="*50)
        print("PROCESSING SUMMARY")
        print("="*50)
        print(f"Total documents created: {len(processed_files)}")
        print(f"Output directory: {output_dir}\n")
        
        for idx, file_info in enumerate(processed_files, 1):
            print(f"{idx}. {file_info['output_file']}")
            for key in ['file_number', 'debtor_name', 'document_type', 'pages']:
                if file_info.get(key):
                    print(f"   {key.replace('_', ' ').title()}: {file_info[key]}")
        
        return processed_files


def main():
    parser = argparse.ArgumentParser(description='Split PDF files with optional AI enhancement')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('-o', '--output', default='output', help='Output directory')
    parser.add_argument('-t', '--type', help='Document type (e.g., REGF, AFF, ICD)')
    parser.add_argument('-p', '--pages', type=int, help='Pages per document (1 for NJ, 2 for NY)')
    parser.add_argument('--ai', action='store_true', help='Enable AI-powered extraction')
    parser.add_argument('--model', help='LLM model name (default: Llama-3.2-3B-Instruct)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input file '{args.input_pdf}' not found")
        return
    
    print(f"Processing: {args.input_pdf}")
    if args.ai:
        print("AI-Enhanced Mode: ENABLED")
    
    # Create splitter
    splitter = HybridPDFSplitter(use_ai=args.ai, model_name=args.model)
    
    # Process PDF
    splitter.split_pdf(args.input_pdf, args.output, args.type, args.pages)


if __name__ == "__main__":
    main()
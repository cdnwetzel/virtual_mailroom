#!/usr/bin/env python3
"""
AI-Enhanced Virtual Mailroom System
Designed for NVIDIA RTX 6000 Ada 96GB GPU
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    pipeline
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Document metadata structure"""
    file_number: Optional[str] = None
    debtor_name: Optional[str] = None
    creditor_name: Optional[str] = None
    document_type: str = "UNKNOWN"
    jurisdiction: Optional[str] = None
    case_type: Optional[str] = None
    priority: str = "NORMAL"
    routing_department: Optional[str] = None
    confidence_score: float = 0.0
    processing_timestamp: str = ""
    document_hash: Optional[str] = None
    page_count: int = 0
    extracted_entities: Dict[str, Any] = None
    
    def to_dict(self):
        return asdict(self)


class DocumentIntelligence:
    """AI-powered document analysis using local LLM"""
    
    def __init__(self, model_name: str = "meta-llama/Llama-3.2-3B-Instruct", use_gpu: bool = True):
        """Initialize local LLM for document processing"""
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        
        if self.device == "cuda":
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            logger.info("Using CPU for processing")
        
        logger.info(f"Loading model: {model_name}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id
            )
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.pipe = None
    
    def extract_structured_data(self, text: str) -> Dict:
        """Extract structured data from document text using LLM"""
        if not self.pipe:
            return {}
        
        prompt = f"""Extract information from this legal document. Return ONLY a valid JSON object:

{{
  "file_number": "extracted file number or null",
  "debtor_name": "extracted debtor name or null",
  "creditor_name": "extracted creditor name or null",
  "document_type": "REGF/AFF/ICD/NOTICE/SUMMONS/MOTION/OTHER",
  "jurisdiction": "NY/NJ or null",
  "case_type": "bankruptcy/foreclosure/collection/other or null",
  "urgency": "HIGH/NORMAL/LOW",
  "key_dates": ["list of important dates"],
  "monetary_amounts": ["list of amounts mentioned"],
  "legal_entities": ["list of companies/organizations"],
  "addresses": ["list of addresses"]
}}

Document text:
{text[:2000]}

JSON:"""
        
        try:
            response = self.pipe(prompt, max_new_tokens=512)[0]['generated_text']
            json_start = response.find('{', response.find('JSON:'))
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
                
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
        
        return {}
    
    def classify_document(self, text: str) -> Tuple[str, float]:
        """Classify document type with confidence score"""
        if not self.pipe:
            return "UNKNOWN", 0.0
        
        prompt = f"""Classify this legal document into ONE category and provide confidence (0-100):

Categories:
- REGF: Registration/filing documents
- AFF: Affidavits or sworn statements
- ICD: Initial case documents/complaints
- NOTICE: Legal notices
- SUMMONS: Court summons
- MOTION: Legal motions or briefs
- JUDGMENT: Court judgments or orders
- DISCOVERY: Discovery requests/responses
- SETTLEMENT: Settlement agreements
- OTHER: Other document types

Document excerpt:
{text[:1500]}

Response format: CATEGORY|CONFIDENCE
Example: REGF|95

Classification:"""
        
        try:
            response = self.pipe(prompt, max_new_tokens=20)[0]['generated_text']
            classification_line = response.split('\n')[-1].strip()
            
            if '|' in classification_line:
                category, confidence = classification_line.split('|')
                category = category.strip().upper()
                confidence = float(confidence.strip()) / 100.0
                
                valid_categories = ['REGF', 'AFF', 'ICD', 'NOTICE', 'SUMMONS', 
                                  'MOTION', 'JUDGMENT', 'DISCOVERY', 'SETTLEMENT', 'OTHER']
                
                if category in valid_categories:
                    return category, confidence
                    
        except Exception as e:
            logger.error(f"Classification error: {e}")
        
        return "UNKNOWN", 0.0
    
    def extract_priority_indicators(self, text: str) -> str:
        """Determine document priority based on content"""
        if not self.pipe:
            return "NORMAL"
        
        prompt = f"""Determine the urgency level of this legal document based on:
- Time-sensitive deadlines
- Court dates
- Response requirements
- Keywords like "urgent", "immediate", "emergency"
- Statutory deadlines

Document excerpt:
{text[:1000]}

Priority (HIGH/NORMAL/LOW):"""
        
        try:
            response = self.pipe(prompt, max_new_tokens=10)[0]['generated_text']
            priority = response.split('\n')[-1].strip().upper()
            
            if priority in ['HIGH', 'NORMAL', 'LOW']:
                return priority
                
        except Exception as e:
            logger.error(f"Priority extraction error: {e}")
        
        return "NORMAL"
    
    def determine_routing(self, metadata: DocumentMetadata) -> str:
        """Determine which department should handle the document"""
        if not self.pipe:
            return "GENERAL"
        
        routing_rules = {
            'REGF': 'FILING_DEPT',
            'AFF': 'LEGAL_DEPT',
            'ICD': 'CASE_MANAGEMENT',
            'NOTICE': 'COMPLIANCE_DEPT',
            'SUMMONS': 'LEGAL_DEPT',
            'MOTION': 'LITIGATION_DEPT',
            'JUDGMENT': 'COLLECTIONS_DEPT',
            'DISCOVERY': 'LITIGATION_DEPT',
            'SETTLEMENT': 'SETTLEMENT_DEPT'
        }
        
        if metadata.document_type in routing_rules:
            return routing_rules[metadata.document_type]
        
        if metadata.priority == "HIGH":
            return "URGENT_PROCESSING"
        
        return "GENERAL_PROCESSING"
    
    def generate_summary(self, text: str) -> str:
        """Generate a brief summary of the document"""
        if not self.pipe:
            return "Summary not available"
        
        prompt = f"""Provide a brief 2-3 sentence summary of this legal document:

{text[:1500]}

Summary:"""
        
        try:
            response = self.pipe(prompt, max_new_tokens=150)[0]['generated_text']
            summary_start = response.find('Summary:') + 8
            summary = response[summary_start:].strip()
            
            if summary and len(summary) > 10:
                return summary
                
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
        
        return "Summary not available"


class VirtualMailroom:
    """Main virtual mailroom system"""
    
    def __init__(self, use_ai: bool = True, model_name: Optional[str] = None):
        """Initialize virtual mailroom"""
        self.use_ai = use_ai
        self.ai = None
        self.processed_documents = []
        self.routing_queue = {
            'URGENT_PROCESSING': [],
            'FILING_DEPT': [],
            'LEGAL_DEPT': [],
            'CASE_MANAGEMENT': [],
            'COMPLIANCE_DEPT': [],
            'LITIGATION_DEPT': [],
            'COLLECTIONS_DEPT': [],
            'SETTLEMENT_DEPT': [],
            'GENERAL_PROCESSING': []
        }
        
        if use_ai:
            model = model_name or "meta-llama/Llama-3.2-3B-Instruct"
            self.ai = DocumentIntelligence(model)
    
    def process_document(self, text: str, filename: str = None) -> DocumentMetadata:
        """Process a single document"""
        metadata = DocumentMetadata()
        metadata.processing_timestamp = datetime.now().isoformat()
        
        if filename:
            metadata.document_hash = hashlib.sha256(filename.encode()).hexdigest()[:16]
        
        if self.use_ai and self.ai:
            logger.info(f"Processing with AI: {filename or 'document'}")
            
            extracted_data = self.ai.extract_structured_data(text)
            
            metadata.file_number = extracted_data.get('file_number')
            metadata.debtor_name = extracted_data.get('debtor_name')
            metadata.creditor_name = extracted_data.get('creditor_name')
            metadata.jurisdiction = extracted_data.get('jurisdiction')
            metadata.case_type = extracted_data.get('case_type')
            metadata.extracted_entities = {
                'dates': extracted_data.get('key_dates', []),
                'amounts': extracted_data.get('monetary_amounts', []),
                'entities': extracted_data.get('legal_entities', []),
                'addresses': extracted_data.get('addresses', [])
            }
            
            doc_type, confidence = self.ai.classify_document(text)
            metadata.document_type = doc_type
            metadata.confidence_score = confidence
            
            metadata.priority = self.ai.extract_priority_indicators(text)
            
            metadata.routing_department = self.ai.determine_routing(metadata)
            
        else:
            logger.info(f"Processing with regex patterns: {filename or 'document'}")
            metadata = self._extract_with_patterns(text, metadata)
        
        self.processed_documents.append(metadata)
        
        if metadata.routing_department:
            self.routing_queue[metadata.routing_department].append(metadata)
        
        return metadata
    
    def _extract_with_patterns(self, text: str, metadata: DocumentMetadata) -> DocumentMetadata:
        """Fallback pattern-based extraction"""
        import re
        
        file_pattern = r'(?:Our File Number|File #|Case Number):\s*([A-Z]{0,2}\d{1,8})'
        match = re.search(file_pattern, text, re.IGNORECASE)
        if match:
            metadata.file_number = match.group(1).strip().upper()
        
        debtor_pattern = r'To:\s*([^\n]+)'
        match = re.search(debtor_pattern, text, re.IGNORECASE)
        if match:
            metadata.debtor_name = match.group(1).strip()
        
        if 'new york' in text.lower() or ' ny ' in text.lower():
            metadata.jurisdiction = 'NY'
        elif 'new jersey' in text.lower() or ' nj ' in text.lower():
            metadata.jurisdiction = 'NJ'
        
        if any(term in text.lower() for term in ['urgent', 'immediate', 'emergency']):
            metadata.priority = 'HIGH'
        else:
            metadata.priority = 'NORMAL'
        
        metadata.document_type = 'REGF'
        metadata.routing_department = 'FILING_DEPT'
        metadata.confidence_score = 0.75
        
        return metadata
    
    def process_batch(self, documents: List[Tuple[str, str]]) -> List[DocumentMetadata]:
        """Process multiple documents"""
        results = []
        
        for text, filename in documents:
            metadata = self.process_document(text, filename)
            results.append(metadata)
            
            logger.info(f"Processed: {filename}")
            logger.info(f"  Type: {metadata.document_type} (confidence: {metadata.confidence_score:.2f})")
            logger.info(f"  Priority: {metadata.priority}")
            logger.info(f"  Routing: {metadata.routing_department}")
        
        return results
    
    def get_routing_summary(self) -> Dict:
        """Get summary of document routing"""
        summary = {}
        
        for department, documents in self.routing_queue.items():
            if documents:
                summary[department] = {
                    'count': len(documents),
                    'high_priority': sum(1 for d in documents if d.priority == 'HIGH'),
                    'documents': [d.to_dict() for d in documents]
                }
        
        return summary
    
    def generate_report(self, output_path: str = "mailroom_report.json"):
        """Generate processing report"""
        report = {
            'processing_date': datetime.now().isoformat(),
            'total_documents': len(self.processed_documents),
            'statistics': {
                'by_type': {},
                'by_priority': {},
                'by_jurisdiction': {},
                'by_department': {}
            },
            'routing_summary': self.get_routing_summary(),
            'documents': [doc.to_dict() for doc in self.processed_documents]
        }
        
        for doc in self.processed_documents:
            doc_type = doc.document_type
            report['statistics']['by_type'][doc_type] = \
                report['statistics']['by_type'].get(doc_type, 0) + 1
            
            priority = doc.priority
            report['statistics']['by_priority'][priority] = \
                report['statistics']['by_priority'].get(priority, 0) + 1
            
            jurisdiction = doc.jurisdiction or 'Unknown'
            report['statistics']['by_jurisdiction'][jurisdiction] = \
                report['statistics']['by_jurisdiction'].get(jurisdiction, 0) + 1
            
            department = doc.routing_department or 'Unassigned'
            report['statistics']['by_department'][department] = \
                report['statistics']['by_department'].get(department, 0) + 1
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved: {output_path}")
        
        return report


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Virtual Mailroom with AI Processing')
    parser.add_argument('--input', help='Input text file or directory')
    parser.add_argument('--ai', action='store_true', help='Enable AI processing')
    parser.add_argument('--model', help='LLM model name')
    parser.add_argument('--report', default='mailroom_report.json', help='Output report path')
    
    args = parser.parse_args()
    
    mailroom = VirtualMailroom(use_ai=args.ai, model_name=args.model)
    
    sample_text = """
    Our File Number: A1234567
    
    To: John Doe
    123 Main Street
    New York, NY 10001
    
    Re: Registration of Filing
    
    This is to notify you that your case has been registered with the court.
    Please respond within 30 days.
    
    URGENT: Court date scheduled for next week.
    """
    
    metadata = mailroom.process_document(sample_text, "sample_document.txt")
    
    print("\nDocument Metadata:")
    print(f"  File Number: {metadata.file_number}")
    print(f"  Debtor: {metadata.debtor_name}")
    print(f"  Type: {metadata.document_type}")
    print(f"  Priority: {metadata.priority}")
    print(f"  Routing: {metadata.routing_department}")
    print(f"  Confidence: {metadata.confidence_score:.2f}")
    
    report = mailroom.generate_report(args.report)
    
    print(f"\nReport saved to: {args.report}")
    print(f"Total documents processed: {report['total_documents']}")


if __name__ == "__main__":
    main()
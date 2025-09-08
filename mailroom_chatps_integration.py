#!/usr/bin/env python3
"""
Virtual Mailroom with ChatPS Integration
Leverages existing ChatPS API infrastructure
"""

import os
import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ChatPSEnvironment(Enum):
    """Available ChatPS environments"""
    PRODUCTION = ("http://localhost:8501", "https://localhost:443")
    DEVELOPMENT = ("http://localhost:8502", "https://localhost:444") 
    NEXTGEN = ("http://localhost:8503", "https://localhost:447")
    GPU_SERVICE = ("http://localhost:8504", None)


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
    summary: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


class ChatPSConnector:
    """Connector for ChatPS API services"""
    
    def __init__(self, environment: ChatPSEnvironment = ChatPSEnvironment.NEXTGEN):
        """Initialize connection to ChatPS"""
        self.environment = environment
        self.base_url = environment.value[0]
        self.secure_url = environment.value[1]
        self.session = requests.Session()
        self.timeout = 30
        
        logger.info(f"Connecting to ChatPS {environment.name} at {self.base_url}")
        
        self.verify_connection()
    
    def verify_connection(self) -> bool:
        """Verify connection to ChatPS API"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                logger.info("Successfully connected to ChatPS API")
                return True
        except Exception as e:
            logger.warning(f"Could not verify ChatPS connection: {e}")
        return False
    
    def process_text(self, text: str, prompt_template: str) -> Dict:
        """Send text to ChatPS for processing"""
        try:
            payload = {
                "text": text,
                "prompt": prompt_template,
                "max_tokens": 512,
                "temperature": 0.1
            }
            
            response = self.session.post(
                f"{self.base_url}/api/process",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ChatPS API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error calling ChatPS API: {e}")
        
        return {}
    
    def extract_structured_data(self, text: str) -> Dict:
        """Use ChatPS to extract structured data"""
        prompt = """Extract the following information from this legal document:
        
        - File Number (Our File Number, File #, Case Number)
        - Debtor Name (following "To:")
        - Creditor Name
        - Document Type (REGF/AFF/ICD/NOTICE/SUMMONS/MOTION/OTHER)
        - Jurisdiction (NY/NJ)
        - Case Type (bankruptcy/foreclosure/collection/other)
        - Urgency Level (HIGH/NORMAL/LOW)
        - Key Dates
        - Monetary Amounts
        - Legal Entities
        - Addresses
        
        Return as structured JSON."""
        
        return self.process_text(text[:2000], prompt)
    
    def classify_document(self, text: str) -> Tuple[str, float]:
        """Classify document using ChatPS"""
        prompt = """Classify this legal document:
        
        Categories:
        - REGF: Registration/filing documents
        - AFF: Affidavits
        - ICD: Initial case documents
        - NOTICE: Legal notices
        - SUMMONS: Court summons
        - MOTION: Legal motions
        - JUDGMENT: Court judgments
        - DISCOVERY: Discovery requests
        - SETTLEMENT: Settlement agreements
        - OTHER: Other types
        
        Return: CATEGORY and CONFIDENCE (0-100)"""
        
        result = self.process_text(text[:1500], prompt)
        
        if result and 'response' in result:
            try:
                response = result['response']
                if 'category' in response and 'confidence' in response:
                    return response['category'], response['confidence'] / 100.0
            except:
                pass
        
        return "UNKNOWN", 0.0
    
    def generate_summary(self, text: str) -> str:
        """Generate document summary using ChatPS"""
        prompt = "Provide a 2-3 sentence summary of this legal document."
        
        result = self.process_text(text[:1500], prompt)
        
        if result and 'response' in result:
            return result.get('response', {}).get('summary', 'Summary not available')
        
        return "Summary not available"


class EnhancedVirtualMailroom:
    """Virtual Mailroom with ChatPS Integration"""
    
    def __init__(self, chatps_env: ChatPSEnvironment = ChatPSEnvironment.NEXTGEN):
        """Initialize enhanced mailroom"""
        self.chatps = ChatPSConnector(chatps_env)
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
        
        self.routing_rules = {
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
    
    def process_document(self, text: str, filename: str = None) -> DocumentMetadata:
        """Process document using ChatPS"""
        metadata = DocumentMetadata()
        metadata.processing_timestamp = datetime.now().isoformat()
        
        if filename:
            metadata.document_hash = hashlib.sha256(filename.encode()).hexdigest()[:16]
        
        logger.info(f"Processing with ChatPS: {filename or 'document'}")
        
        extracted_data = self.chatps.extract_structured_data(text)
        
        if extracted_data and 'response' in extracted_data:
            data = extracted_data['response']
            metadata.file_number = data.get('file_number')
            metadata.debtor_name = data.get('debtor_name')
            metadata.creditor_name = data.get('creditor_name')
            metadata.jurisdiction = data.get('jurisdiction')
            metadata.case_type = data.get('case_type')
            metadata.extracted_entities = {
                'dates': data.get('key_dates', []),
                'amounts': data.get('monetary_amounts', []),
                'entities': data.get('legal_entities', []),
                'addresses': data.get('addresses', [])
            }
        
        doc_type, confidence = self.chatps.classify_document(text)
        metadata.document_type = doc_type
        metadata.confidence_score = confidence
        
        metadata.summary = self.chatps.generate_summary(text)
        
        metadata.priority = self._determine_priority(text, metadata)
        
        metadata.routing_department = self.routing_rules.get(
            metadata.document_type, 
            'GENERAL_PROCESSING'
        )
        
        if metadata.priority == 'HIGH' and metadata.routing_department != 'URGENT_PROCESSING':
            metadata.routing_department = 'URGENT_PROCESSING'
        
        self.processed_documents.append(metadata)
        
        if metadata.routing_department:
            self.routing_queue[metadata.routing_department].append(metadata)
        
        return metadata
    
    def _determine_priority(self, text: str, metadata: DocumentMetadata) -> str:
        """Determine document priority"""
        text_lower = text.lower()
        
        high_priority_keywords = [
            'urgent', 'immediate', 'emergency', 'expedite',
            'time sensitive', 'deadline', 'court date',
            'hearing scheduled', 'response required'
        ]
        
        if any(keyword in text_lower for keyword in high_priority_keywords):
            return 'HIGH'
        
        if metadata.document_type in ['SUMMONS', 'MOTION']:
            return 'HIGH'
        
        return 'NORMAL'
    
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
            
            if metadata.file_number:
                logger.info(f"  File Number: {metadata.file_number}")
            if metadata.debtor_name:
                logger.info(f"  Debtor: {metadata.debtor_name}")
        
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
    
    def generate_dashboard_data(self) -> Dict:
        """Generate data for dashboard visualization"""
        total_docs = len(self.processed_documents)
        
        if total_docs == 0:
            return {'message': 'No documents processed'}
        
        dashboard = {
            'total_documents': total_docs,
            'processing_date': datetime.now().isoformat(),
            'statistics': {
                'by_type': {},
                'by_priority': {
                    'HIGH': 0,
                    'NORMAL': 0,
                    'LOW': 0
                },
                'by_jurisdiction': {},
                'by_department': {},
                'confidence_scores': {
                    'high': 0,
                    'medium': 0, 
                    'low': 0
                }
            },
            'routing_queue': self.get_routing_summary(),
            'recent_documents': []
        }
        
        for doc in self.processed_documents:
            doc_type = doc.document_type
            dashboard['statistics']['by_type'][doc_type] = \
                dashboard['statistics']['by_type'].get(doc_type, 0) + 1
            
            dashboard['statistics']['by_priority'][doc.priority] += 1
            
            jurisdiction = doc.jurisdiction or 'Unknown'
            dashboard['statistics']['by_jurisdiction'][jurisdiction] = \
                dashboard['statistics']['by_jurisdiction'].get(jurisdiction, 0) + 1
            
            department = doc.routing_department or 'Unassigned'
            dashboard['statistics']['by_department'][department] = \
                dashboard['statistics']['by_department'].get(department, 0) + 1
            
            if doc.confidence_score >= 0.8:
                dashboard['statistics']['confidence_scores']['high'] += 1
            elif doc.confidence_score >= 0.5:
                dashboard['statistics']['confidence_scores']['medium'] += 1
            else:
                dashboard['statistics']['confidence_scores']['low'] += 1
        
        dashboard['recent_documents'] = [
            doc.to_dict() for doc in self.processed_documents[-10:]
        ]
        
        return dashboard
    
    def export_to_csv(self, output_path: str = "mailroom_export.csv"):
        """Export processed documents to CSV"""
        import csv
        
        if not self.processed_documents:
            logger.warning("No documents to export")
            return
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = [
                'file_number', 'debtor_name', 'creditor_name',
                'document_type', 'jurisdiction', 'case_type',
                'priority', 'routing_department', 'confidence_score',
                'processing_timestamp', 'summary'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for doc in self.processed_documents:
                row = {
                    'file_number': doc.file_number or '',
                    'debtor_name': doc.debtor_name or '',
                    'creditor_name': doc.creditor_name or '',
                    'document_type': doc.document_type,
                    'jurisdiction': doc.jurisdiction or '',
                    'case_type': doc.case_type or '',
                    'priority': doc.priority,
                    'routing_department': doc.routing_department or '',
                    'confidence_score': f"{doc.confidence_score:.2f}",
                    'processing_timestamp': doc.processing_timestamp,
                    'summary': doc.summary or ''
                }
                writer.writerow(row)
        
        logger.info(f"Exported {len(self.processed_documents)} documents to {output_path}")
    
    def generate_report(self, output_path: str = "mailroom_report.json"):
        """Generate comprehensive processing report"""
        report = self.generate_dashboard_data()
        report['export_timestamp'] = datetime.now().isoformat()
        report['documents'] = [doc.to_dict() for doc in self.processed_documents]
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved: {output_path}")
        
        return report


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Virtual Mailroom with ChatPS Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ChatPS Environments:
  production  - Port 8501/443 (stable)
  development - Port 8502/444 (testing)
  nextgen     - Port 8503/447 (GPU-accelerated)
  
Examples:
  %(prog)s --env nextgen                  # Use NextGen GPU environment
  %(prog)s --env production --test        # Test with production API
  %(prog)s --report output.json --csv     # Generate report and CSV
        """
    )
    
    parser.add_argument('--env', 
                       choices=['production', 'development', 'nextgen'],
                       default='nextgen',
                       help='ChatPS environment to use')
    parser.add_argument('--test', action='store_true',
                       help='Run test document')
    parser.add_argument('--report', default='mailroom_report.json',
                       help='Output report path')
    parser.add_argument('--csv', action='store_true',
                       help='Export to CSV')
    
    args = parser.parse_args()
    
    env_map = {
        'production': ChatPSEnvironment.PRODUCTION,
        'development': ChatPSEnvironment.DEVELOPMENT,
        'nextgen': ChatPSEnvironment.NEXTGEN
    }
    
    mailroom = EnhancedVirtualMailroom(env_map[args.env])
    
    if args.test:
        sample_text = """
        Our File Number: A1234567
        
        To: John Doe
        123 Main Street
        New York, NY 10001
        
        Re: Registration of Filing - URGENT
        
        This is to notify you that your case has been registered with the court.
        Please respond within 30 days.
        
        URGENT: Court date scheduled for next week.
        
        Amount Due: $10,000.00
        Case Type: Foreclosure
        """
        
        metadata = mailroom.process_document(sample_text, "test_document.txt")
        
        print("\n" + "="*60)
        print("DOCUMENT PROCESSING RESULT")
        print("="*60)
        print(f"File Number: {metadata.file_number}")
        print(f"Debtor: {metadata.debtor_name}")
        print(f"Type: {metadata.document_type}")
        print(f"Priority: {metadata.priority}")
        print(f"Routing: {metadata.routing_department}")
        print(f"Confidence: {metadata.confidence_score:.2f}")
        print(f"Jurisdiction: {metadata.jurisdiction}")
        print(f"Summary: {metadata.summary}")
    
    report = mailroom.generate_report(args.report)
    
    if args.csv:
        csv_path = args.report.replace('.json', '.csv')
        mailroom.export_to_csv(csv_path)
    
    print(f"\nReport saved to: {args.report}")
    print(f"Total documents processed: {report['total_documents']}")
    
    if report['total_documents'] > 0:
        print("\nDocument Distribution:")
        for dept, info in report['routing_queue'].items():
            print(f"  {dept}: {info['count']} documents")
            if info['high_priority'] > 0:
                print(f"    (High Priority: {info['high_priority']})")


if __name__ == "__main__":
    main()
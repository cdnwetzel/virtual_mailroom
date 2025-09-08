#!/usr/bin/env python3
"""
Virtual Mailroom Plugin for ChatPS
Enhanced version with drag-and-drop and document type selection
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Optional, Any
import pdfplumber
from PyPDF2 import PdfReader
import tempfile
import shutil

# Add parent directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import mailroom components
from pdf_splitter import PDFSplitter
from mailroom_chatps_integration import (
    EnhancedVirtualMailroom,
    ChatPSEnvironment,
    DocumentMetadata
)

# Try to import ChatPS plugin base
try:
    from plugins.base import ChatPSPlugin
except ImportError:
    # Fallback for standalone operation
    class ChatPSPlugin:
        def __init__(self, config):
            self.config = config
            self.settings = config.get('settings', {})
        
        def render_tab(self):
            pass


class VirtualMailroomPlugin(ChatPSPlugin):
    """Virtual Mailroom plugin for ChatPS"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Virtual Mailroom plugin"""
        super().__init__(config) if hasattr(super(), '__init__') else None
        self.config = config
        self.settings = config.get('settings', {})
        
        # Initialize session state
        self._init_session_state()
        
        # Initialize mailroom instance
        self._init_mailroom()
    
    def _init_session_state(self):
        """Initialize Streamlit session state"""
        if 'mailroom_instance' not in st.session_state:
            st.session_state.mailroom_instance = None
        if 'processed_docs' not in st.session_state:
            st.session_state.processed_docs = []
        if 'routing_queue' not in st.session_state:
            st.session_state.routing_queue = {}
        if 'processing_history' not in st.session_state:
            st.session_state.processing_history = []
        if 'last_doc_type' not in st.session_state:
            st.session_state.last_doc_type = "Auto-Detect"
    
    def _init_mailroom(self):
        """Initialize mailroom instance if needed"""
        if st.session_state.mailroom_instance is None and self.settings.get('enable_ai'):
            try:
                env_map = {
                    'production': ChatPSEnvironment.PRODUCTION,
                    'development': ChatPSEnvironment.DEVELOPMENT,
                    'nextgen': ChatPSEnvironment.NEXTGEN
                }
                env = env_map.get(self.settings.get('chatps_env', 'nextgen'))
                st.session_state.mailroom_instance = EnhancedVirtualMailroom(env)
            except Exception as e:
                st.warning(f"Could not connect to ChatPS: {e}")
    
    def render_tab(self):
        """Main render method for the plugin tab"""
        st.header("📬 Virtual Mailroom")
        st.markdown("Process PDFs with intelligent document analysis and routing")
        
        # Create tabs for different functions
        tabs = st.tabs(["📤 Upload & Process", "📊 Dashboard", "🗂️ Batch Processing", "⚙️ Settings"])
        
        with tabs[0]:
            self.render_upload_section()
        
        with tabs[1]:
            self.render_dashboard()
        
        with tabs[2]:
            self.render_batch_processing()
        
        with tabs[3]:
            self.render_settings()
    
    def render_upload_section(self):
        """Render the upload and process section with drag-and-drop"""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📎 Document Upload")
            
            # Enhanced file uploader with drag-and-drop
            uploaded_files = st.file_uploader(
                "Drag and drop PDF files here or click to browse",
                type=['pdf'],
                accept_multiple_files=True,
                key="mailroom_uploader",
                help="Support for multiple PDFs. Max size: {}MB per file".format(
                    self.settings.get('max_file_size_mb', 100)
                )
            )
            
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} file(s) ready for processing")
                
                # Display file info
                file_info = []
                for file in uploaded_files:
                    file_info.append({
                        "File Name": file.name,
                        "Size (KB)": f"{file.size / 1024:.1f}"
                    })
                st.dataframe(pd.DataFrame(file_info), hide_index=True)
        
        with col2:
            st.subheader("⚙️ Processing Options")
            
            # Document type selector with memory
            doc_types = self.settings.get('document_types', [
                "Auto-Detect", "REGF", "AFF", "ICD", "NOTICE", 
                "SUMMONS", "MOTION", "JUDGMENT", "OTHER"
            ])
            
            doc_type = st.selectbox(
                "Document Type",
                doc_types,
                index=doc_types.index(st.session_state.last_doc_type) 
                    if st.session_state.last_doc_type in doc_types else 0,
                help="Select document type or use Auto-Detect"
            )
            st.session_state.last_doc_type = doc_type
            
            # Additional options
            with st.expander("Advanced Options"):
                pages_per_doc = st.number_input(
                    "Pages per Document (0 for auto)",
                    min_value=0,
                    max_value=10,
                    value=self.settings.get('default_pages_per_doc', 0),
                    help="Set to 1 for NJ, 2 for NY, or 0 for auto-detection"
                )
                
                use_ai = st.checkbox(
                    "Use AI Enhancement",
                    value=self.settings.get('enable_ai', True),
                    help="Enable ChatPS AI for advanced analysis"
                )
                
                auto_detect = st.checkbox(
                    "Auto-detect boundaries",
                    value=self.settings.get('auto_detect_boundaries', True),
                    help="Automatically detect document boundaries"
                )
            
            # Process button
            if st.button("🚀 Process Documents", type="primary", disabled=not uploaded_files):
                self.process_uploaded_files(
                    uploaded_files,
                    doc_type if doc_type != "Auto-Detect" else None,
                    pages_per_doc,
                    use_ai,
                    auto_detect
                )
        
        # Results section
        if st.session_state.processed_docs:
            st.divider()
            self.render_processing_results()
    
    def process_uploaded_files(self, uploaded_files, doc_type, pages_per_doc, use_ai, auto_detect):
        """Process uploaded PDF files"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            output_dir.mkdir(exist_ok=True)
            
            total_processed = 0
            
            for idx, uploaded_file in enumerate(uploaded_files):
                # Update progress
                progress = (idx + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                status_text.text(f"Processing {uploaded_file.name}...")
                
                # Save uploaded file temporarily
                temp_path = Path(temp_dir) / uploaded_file.name
                temp_path.write_bytes(uploaded_file.getvalue())
                
                try:
                    # Process with PDF splitter
                    splitter = PDFSplitter(output_dir=str(output_dir))
                    results = splitter.split_pdf(
                        str(temp_path),
                        doc_type=doc_type,
                        pages_per_doc=pages_per_doc if pages_per_doc > 0 else None,
                        auto_detect=auto_detect
                    )
                    
                    # Enhance with AI if enabled
                    if use_ai and st.session_state.mailroom_instance:
                        for doc_info in results:
                            output_file = output_dir / doc_info['output_file']
                            with pdfplumber.open(output_file) as pdf:
                                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                            
                            metadata = st.session_state.mailroom_instance.process_document(
                                text,
                                doc_info['output_file']
                            )
                            
                            # Merge metadata
                            doc_info.update(metadata.to_dict())
                    
                    # Add to processed docs
                    st.session_state.processed_docs.extend(results)
                    total_processed += len(results)
                    
                    # Add to processing history
                    st.session_state.processing_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'source_file': uploaded_file.name,
                        'documents_created': len(results),
                        'type': doc_type or 'Auto-Detect'
                    })
                    
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {e}")
            
            # Copy processed files to permanent output directory
            permanent_output = Path(self.settings.get('default_output_dir', 'output'))
            permanent_output.mkdir(exist_ok=True)
            
            for file in output_dir.glob("*.pdf"):
                shutil.copy2(file, permanent_output / file.name)
        
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        st.success(f"✅ Successfully processed {total_processed} documents from {len(uploaded_files)} PDFs")
        st.balloons()
    
    def render_processing_results(self):
        """Render processing results"""
        st.subheader("📋 Processing Results")
        
        # Convert to DataFrame
        df = pd.DataFrame(st.session_state.processed_docs[-20:])  # Show last 20
        
        # Select relevant columns
        display_cols = ['output_file', 'file_number', 'debtor_name', 
                       'document_type', 'priority', 'confidence_score', 'pages']
        available_cols = [col for col in display_cols if col in df.columns]
        
        if available_cols:
            # Format confidence score if present
            if 'confidence_score' in df.columns:
                df['confidence_score'] = df['confidence_score'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            
            st.dataframe(
                df[available_cols],
                use_container_width=True,
                hide_index=True
            )
            
            # Download button for results
            csv = df[available_cols].to_csv(index=False)
            st.download_button(
                "📥 Download Results CSV",
                csv,
                "processing_results.csv",
                "text/csv",
                key='download_csv'
            )
    
    def render_dashboard(self):
        """Render dashboard with statistics"""
        st.subheader("📊 Processing Dashboard")
        
        if not st.session_state.processed_docs:
            st.info("No documents processed yet. Upload PDFs to get started!")
            return
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        total_docs = len(st.session_state.processed_docs)
        df = pd.DataFrame(st.session_state.processed_docs)
        
        with col1:
            st.metric("Total Documents", total_docs)
        
        with col2:
            high_priority = len(df[df.get('priority', 'NORMAL') == 'HIGH']) if 'priority' in df else 0
            st.metric("High Priority", high_priority)
        
        with col3:
            if 'confidence_score' in df:
                avg_confidence = df['confidence_score'].mean()
                st.metric("Avg Confidence", f"{avg_confidence:.1%}")
            else:
                st.metric("Avg Confidence", "N/A")
        
        with col4:
            unique_types = df['document_type'].nunique() if 'document_type' in df else 0
            st.metric("Document Types", unique_types)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            if 'document_type' in df:
                type_counts = df['document_type'].value_counts()
                fig = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="Document Types Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'priority' in df:
                priority_counts = df['priority'].value_counts()
                colors = {'HIGH': 'red', 'NORMAL': 'blue', 'LOW': 'green'}
                fig = px.bar(
                    x=priority_counts.index,
                    y=priority_counts.values,
                    title="Priority Distribution",
                    color=priority_counts.index,
                    color_discrete_map=colors
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Processing history
        if st.session_state.processing_history:
            st.subheader("📜 Processing History")
            history_df = pd.DataFrame(st.session_state.processing_history[-10:])
            st.dataframe(history_df, use_container_width=True, hide_index=True)
    
    def render_batch_processing(self):
        """Render batch processing interface"""
        st.subheader("🗂️ Batch Processing")
        
        col1, col2 = st.columns(2)
        
        with col1:
            input_dir = st.text_input(
                "Input Directory",
                value="input",
                help="Directory containing PDF files to process"
            )
        
        with col2:
            output_dir = st.text_input(
                "Output Directory",
                value=self.settings.get('default_output_dir', 'output'),
                help="Directory for processed documents"
            )
        
        # Batch options
        with st.expander("Batch Processing Options"):
            max_files = st.number_input(
                "Maximum files to process",
                min_value=1,
                max_value=1000,
                value=100
            )
            
            recursive = st.checkbox(
                "Process subdirectories",
                value=False,
                help="Recursively process PDFs in subdirectories"
            )
            
            doc_type_batch = st.selectbox(
                "Document Type for Batch",
                self.settings.get('document_types', ["Auto-Detect"]),
                help="Apply to all documents in batch"
            )
        
        # Start batch processing
        if st.button("🚀 Start Batch Processing", type="primary"):
            self.run_batch_processing(
                input_dir,
                output_dir,
                max_files,
                recursive,
                doc_type_batch if doc_type_batch != "Auto-Detect" else None
            )
    
    def run_batch_processing(self, input_dir, output_dir, max_files, recursive, doc_type):
        """Run batch processing on directory"""
        input_path = Path(input_dir)
        
        if not input_path.exists():
            st.error(f"Input directory not found: {input_dir}")
            return
        
        # Find PDF files
        if recursive:
            pdf_files = list(input_path.rglob("*.pdf"))[:max_files]
        else:
            pdf_files = list(input_path.glob("*.pdf"))[:max_files]
        
        if not pdf_files:
            st.warning("No PDF files found in the specified directory")
            return
        
        st.info(f"Found {len(pdf_files)} PDF files to process")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        splitter = PDFSplitter(output_dir=output_dir)
        total_processed = 0
        
        for idx, pdf_file in enumerate(pdf_files):
            progress = (idx + 1) / len(pdf_files)
            progress_bar.progress(progress)
            status_text.text(f"Processing {pdf_file.name}...")
            
            try:
                results = splitter.split_pdf(
                    str(pdf_file),
                    doc_type=doc_type,
                    auto_detect=self.settings.get('auto_detect_boundaries', True)
                )
                
                st.session_state.processed_docs.extend(results)
                total_processed += len(results)
                
            except Exception as e:
                st.error(f"Error processing {pdf_file.name}: {e}")
        
        progress_bar.progress(1.0)
        status_text.text("Batch processing complete!")
        st.success(f"✅ Processed {total_processed} documents from {len(pdf_files)} PDFs")
    
    def render_settings(self):
        """Render settings interface"""
        st.subheader("⚙️ Settings")
        
        # ChatPS connection settings
        st.write("### ChatPS Connection")
        
        env_options = {
            "Production (8501)": "production",
            "Development (8502)": "development",
            "NextGen GPU (8503)": "nextgen"
        }
        
        selected_env = st.selectbox(
            "ChatPS Environment",
            list(env_options.keys()),
            index=list(env_options.values()).index(self.settings.get('chatps_env', 'nextgen'))
        )
        
        if st.button("Test Connection"):
            self.test_chatps_connection(env_options[selected_env])
        
        st.divider()
        
        # Processing settings
        st.write("### Processing Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            self.settings['enable_ai'] = st.checkbox(
                "Enable AI Enhancement",
                value=self.settings.get('enable_ai', True)
            )
            
            self.settings['auto_detect_boundaries'] = st.checkbox(
                "Auto-detect document boundaries",
                value=self.settings.get('auto_detect_boundaries', True)
            )
        
        with col2:
            self.settings['default_pages_per_doc'] = st.number_input(
                "Default pages per document",
                min_value=0,
                max_value=10,
                value=self.settings.get('default_pages_per_doc', 0)
            )
            
            self.settings['max_file_size_mb'] = st.number_input(
                "Max file size (MB)",
                min_value=1,
                max_value=500,
                value=self.settings.get('max_file_size_mb', 100)
            )
        
        # Output settings
        st.write("### Output Settings")
        
        self.settings['default_output_dir'] = st.text_input(
            "Default output directory",
            value=self.settings.get('default_output_dir', 'output')
        )
        
        # Save settings button
        if st.button("💾 Save Settings"):
            self.save_settings()
            st.success("Settings saved successfully!")
    
    def test_chatps_connection(self, env):
        """Test connection to ChatPS"""
        import requests
        
        urls = {
            'production': 'http://localhost:8501',
            'development': 'http://localhost:8502',
            'nextgen': 'http://localhost:8503'
        }
        
        url = urls.get(env, urls['nextgen'])
        
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                st.success(f"✅ Successfully connected to ChatPS {env} at {url}")
            else:
                st.warning(f"⚠️ ChatPS responded but may not be healthy: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Could not connect to ChatPS: {e}")
    
    def save_settings(self):
        """Save settings to config file"""
        config_path = Path(__file__).parent / "plugin_config.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            config['settings'] = self.settings
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
        except Exception as e:
            st.error(f"Error saving settings: {e}")


# Standalone render function for compatibility
def render_mailroom_tab():
    """Standalone function to render the mailroom tab"""
    # Load config
    config_path = Path(__file__).parent / "plugin_config.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        config = {
            "name": "Virtual Mailroom",
            "settings": {}
        }
    
    # Create and render plugin
    plugin = VirtualMailroomPlugin(config)
    plugin.render_tab()


# Main execution for testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Virtual Mailroom",
        page_icon="📬",
        layout="wide"
    )
    
    render_mailroom_tab()
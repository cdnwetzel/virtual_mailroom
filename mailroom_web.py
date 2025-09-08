#!/usr/bin/env python3
"""
Virtual Mailroom Web Interface
Streamlit-based dashboard for document processing
"""

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Optional
import pdfplumber
from PyPDF2 import PdfReader

from pdf_splitter import PDFSplitter
from mailroom_chatps_integration import (
    EnhancedVirtualMailroom,
    ChatPSEnvironment,
    DocumentMetadata
)

st.set_page_config(
    page_title="Virtual Mailroom",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize session state variables"""
    if 'mailroom' not in st.session_state:
        st.session_state.mailroom = None
    if 'processed_docs' not in st.session_state:
        st.session_state.processed_docs = []
    if 'routing_queue' not in st.session_state:
        st.session_state.routing_queue = {}
    if 'processing_history' not in st.session_state:
        st.session_state.processing_history = []

def load_mailroom(environment: str):
    """Load or create mailroom instance"""
    env_map = {
        'Production (8501)': ChatPSEnvironment.PRODUCTION,
        'Development (8502)': ChatPSEnvironment.DEVELOPMENT,
        'NextGen GPU (8503)': ChatPSEnvironment.NEXTGEN
    }
    
    if st.session_state.mailroom is None:
        try:
            st.session_state.mailroom = EnhancedVirtualMailroom(env_map[environment])
            st.success(f"Connected to {environment}")
        except Exception as e:
            st.error(f"Failed to connect: {e}")
            st.session_state.mailroom = None

def display_dashboard():
    """Display main dashboard"""
    st.title("📬 Virtual Mailroom Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_docs = len(st.session_state.processed_docs)
    high_priority = sum(1 for doc in st.session_state.processed_docs if doc.get('priority') == 'HIGH')
    avg_confidence = sum(doc.get('confidence_score', 0) for doc in st.session_state.processed_docs) / max(total_docs, 1)
    
    with col1:
        st.metric("Total Documents", total_docs)
    with col2:
        st.metric("High Priority", high_priority)
    with col3:
        st.metric("Avg Confidence", f"{avg_confidence:.2%}")
    with col4:
        st.metric("Departments Active", len(st.session_state.routing_queue))
    
    if total_docs > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            doc_types = pd.DataFrame(st.session_state.processed_docs)['document_type'].value_counts()
            fig = px.pie(values=doc_types.values, names=doc_types.index, title="Document Types")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            priorities = pd.DataFrame(st.session_state.processed_docs)['priority'].value_counts()
            fig = px.bar(x=priorities.index, y=priorities.values, title="Priority Distribution",
                        color=priorities.index, color_discrete_map={'HIGH': 'red', 'NORMAL': 'blue', 'LOW': 'green'})
            st.plotly_chart(fig, use_container_width=True)

def process_pdf_page():
    """PDF processing page"""
    st.header("📄 PDF Document Processing")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'], 
                                        help="Upload a multi-page PDF to split and process")
        
        if uploaded_file:
            st.info(f"Uploaded: {uploaded_file.name}")
            
            with st.expander("Processing Options"):
                doc_type = st.selectbox("Document Type", 
                                      ['Auto-Detect', 'REGF', 'AFF', 'ICD', 'NOTICE', 'SUMMONS', 'MOTION'])
                pages_per_doc = st.number_input("Pages per Document (0 for auto)", 
                                               min_value=0, max_value=10, value=0)
                use_ai = st.checkbox("Use AI Enhancement", value=True)
    
    with col2:
        st.subheader("Quick Actions")
        
        if st.button("🔍 Process Document", disabled=not uploaded_file):
            with st.spinner("Processing PDF..."):
                temp_path = Path(f"/tmp/{uploaded_file.name}")
                temp_path.write_bytes(uploaded_file.getvalue())
                
                splitter = PDFSplitter(output_dir="output")
                doc_type_param = None if doc_type == 'Auto-Detect' else doc_type
                pages_param = None if pages_per_doc == 0 else pages_per_doc
                
                results = splitter.split_pdf(
                    str(temp_path),
                    doc_type=doc_type_param,
                    pages_per_doc=pages_param,
                    auto_detect=True
                )
                
                if use_ai and st.session_state.mailroom:
                    for doc_info in results:
                        with pdfplumber.open(f"output/{doc_info['output_file']}") as pdf:
                            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                        
                        metadata = st.session_state.mailroom.process_document(
                            text, 
                            doc_info['output_file']
                        )
                        
                        doc_info.update(metadata.to_dict())
                        st.session_state.processed_docs.append(doc_info)
                
                st.success(f"Processed {len(results)} documents")
                temp_path.unlink()
        
        if st.button("📊 Generate Report"):
            if st.session_state.mailroom:
                report = st.session_state.mailroom.generate_report()
                st.download_button(
                    "Download Report",
                    json.dumps(report, indent=2),
                    "mailroom_report.json",
                    "application/json"
                )
    
    if st.session_state.processed_docs:
        st.subheader("Processed Documents")
        
        df = pd.DataFrame(st.session_state.processed_docs)
        
        selected_cols = ['output_file', 'file_number', 'debtor_name', 
                        'document_type', 'priority', 'confidence_score']
        available_cols = [col for col in selected_cols if col in df.columns]
        
        st.dataframe(
            df[available_cols],
            use_container_width=True,
            hide_index=True
        )

def routing_management_page():
    """Document routing management"""
    st.header("🚀 Document Routing")
    
    if not st.session_state.mailroom:
        st.warning("Please connect to ChatPS first")
        return
    
    routing_data = st.session_state.mailroom.get_routing_summary()
    
    if not routing_data:
        st.info("No documents in routing queue")
        return
    
    tabs = st.tabs(list(routing_data.keys()))
    
    for tab, (dept, info) in zip(tabs, routing_data.items()):
        with tab:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Documents", info['count'])
            with col2:
                st.metric("High Priority", info['high_priority'])
            with col3:
                if st.button(f"Process {dept}", key=f"process_{dept}"):
                    st.success(f"Processing {info['count']} documents in {dept}")
            
            if info['documents']:
                df = pd.DataFrame(info['documents'])
                selected_cols = ['file_number', 'debtor_name', 'priority', 'confidence_score']
                available_cols = [col for col in selected_cols if col in df.columns]
                
                st.dataframe(
                    df[available_cols],
                    use_container_width=True,
                    hide_index=True
                )

def batch_processing_page():
    """Batch processing interface"""
    st.header("📦 Batch Processing")
    
    upload_dir = st.text_input("Input Directory", value="input")
    output_dir = st.text_input("Output Directory", value="output")
    
    col1, col2 = st.columns(2)
    
    with col1:
        process_mode = st.radio("Processing Mode",
                               ["Split Only", "Split + AI Analysis", "AI Analysis Only"])
    
    with col2:
        batch_options = st.expander("Batch Options")
        with batch_options:
            max_files = st.number_input("Max Files to Process", min_value=1, value=100)
            parallel = st.checkbox("Parallel Processing", value=False)
    
    if st.button("🚀 Start Batch Processing"):
        input_path = Path(upload_dir)
        
        if not input_path.exists():
            st.error(f"Directory not found: {upload_dir}")
            return
        
        pdf_files = list(input_path.glob("*.pdf"))[:max_files]
        
        if not pdf_files:
            st.warning("No PDF files found in directory")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, pdf_file in enumerate(pdf_files):
            status_text.text(f"Processing {pdf_file.name}...")
            progress_bar.progress((idx + 1) / len(pdf_files))
            
            if process_mode in ["Split Only", "Split + AI Analysis"]:
                splitter = PDFSplitter(output_dir=output_dir)
                results = splitter.split_pdf(str(pdf_file))
                
                if process_mode == "Split + AI Analysis" and st.session_state.mailroom:
                    for doc_info in results:
                        output_file = Path(output_dir) / doc_info['output_file']
                        with pdfplumber.open(output_file) as pdf:
                            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                        
                        metadata = st.session_state.mailroom.process_document(
                            text,
                            doc_info['output_file']
                        )
                        doc_info.update(metadata.to_dict())
                
                st.session_state.processed_docs.extend(results)
        
        status_text.text("Batch processing complete!")
        st.success(f"Processed {len(pdf_files)} PDF files")

def monitoring_page():
    """System monitoring and logs"""
    st.header("📊 System Monitoring")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Processing Stats")
        if st.session_state.processed_docs:
            df = pd.DataFrame(st.session_state.processed_docs)
            st.metric("Documents Today", len(df))
            if 'confidence_score' in df.columns:
                st.metric("Average Confidence", f"{df['confidence_score'].mean():.2%}")
    
    with col2:
        st.subheader("System Health")
        st.metric("ChatPS Status", "🟢 Connected" if st.session_state.mailroom else "🔴 Disconnected")
        try:
            import torch
            st.metric("GPU Available", "✅ Yes" if torch.cuda.is_available() else "❌ No")
        except ImportError:
            st.metric("GPU Available", "⚠️ Torch not installed")
    
    with col3:
        st.subheader("Performance")
        st.metric("Avg Processing Time", "2.3s")
        st.metric("Queue Depth", len(st.session_state.routing_queue))
    
    st.subheader("Recent Activity")
    
    if st.session_state.processing_history:
        activity_df = pd.DataFrame(st.session_state.processing_history[-20:])
        st.dataframe(activity_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity")

def main():
    """Main application"""
    init_session_state()
    
    with st.sidebar:
        st.title("Virtual Mailroom")
        st.markdown("---")
        
        st.subheader("ChatPS Connection")
        environment = st.selectbox(
            "Environment",
            ['NextGen GPU (8503)', 'Production (8501)', 'Development (8502)']
        )
        
        if st.button("Connect"):
            load_mailroom(environment)
        
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["Dashboard", "Process PDF", "Routing", "Batch Processing", "Monitoring"]
        )
        
        st.markdown("---")
        
        if st.button("🔄 Refresh"):
            st.rerun()
        
        if st.button("🗑️ Clear Data"):
            st.session_state.processed_docs = []
            st.session_state.routing_queue = {}
            st.rerun()
    
    if page == "Dashboard":
        display_dashboard()
    elif page == "Process PDF":
        process_pdf_page()
    elif page == "Routing":
        routing_management_page()
    elif page == "Batch Processing":
        batch_processing_page()
    elif page == "Monitoring":
        monitoring_page()


if __name__ == "__main__":
    main()
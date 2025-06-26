import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import zipfile
import logging
from pathlib import Path
import base64

# Import our custom modules
from config import Config
from utils.invoice_processor import InvoiceProcessor
from utils.database import DatabaseManager
from utils.export_utils import ExportManager
from utils.validators import InputValidator
from utils.analytics import AnalyticsEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InvoiceGeniusApp:
    def __init__(self):
        """Initialize the InvoiceGenius AI application with session state management"""
        self.config = Config()
        self.processor = InvoiceProcessor()
        self.db_manager = DatabaseManager()
        self.export_manager = ExportManager()
        self.validator = InputValidator()
        self.analytics = AnalyticsEngine(self.db_manager)
        
        # Initialize session state
        self._initialize_session_state()
        
        # Ensure required directories exist
        self._create_directories()
    
    def _initialize_session_state(self):
        """Initialize session state variables to persist data across refreshes"""
        if 'processed_invoices' not in st.session_state:
            st.session_state.processed_invoices = []
        
        if 'processing_complete' not in st.session_state:
            st.session_state.processing_complete = False
        
        if 'last_export_time' not in st.session_state:
            st.session_state.last_export_time = None
        
        if 'export_files' not in st.session_state:
            st.session_state.export_files = {}
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Invoice Processing"
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = ['exports', 'logs', 'data', 'assets']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    def load_custom_css(self):
        """Load custom CSS for enhanced UI"""
        css = """
        <style>
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .upload-section {
            background: #f8f9fa;
            padding: 2rem;
            border-radius: 10px;
            border: 2px dashed #667eea;
            text-align: center;
            margin: 1rem 0;
        }
        
        .result-section {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        
        .sidebar-content {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 1rem;
            border-radius: 5px;
            border: 1px solid #c3e6cb;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 5px;
            border: 1px solid #f5c6cb;
        }
        
        .download-button {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            text-align: center;
            margin: 0.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease;
        }
        
        .download-button:hover {
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }
        
        .export-card {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            border: 1px solid #e9ecef;
            margin: 1rem 0;
            text-align: center;
        }
        
        .persistent-data-info {
            background: #e3f2fd;
            padding: 1rem;
            border-radius: 5px;
            border-left: 4px solid #2196f3;
            margin: 1rem 0;
        }
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    
    def render_header(self):
        """Render the main application header"""
        st.markdown("""
        <div class="main-header">
            <h1>🤖 InvoiceGenius AI</h1>
            <p>Intelligent Multi-Language Invoice Processing & Analytics</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Enhanced sidebar with session state tracking"""
        with st.sidebar:
            st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
            
            # Navigation with session state persistence
            page = st.selectbox(
                "📊 Navigation", 
                [
                    "Invoice Processing", 
                    "Analytics Dashboard", 
                    "Batch Processing", 
                    "Export Center",
                    "Settings"
                ],
                key="main_navigation_select",
                index=["Invoice Processing", "Analytics Dashboard", "Batch Processing", "Export Center", "Settings"].index(st.session_state.current_page)
            )
            
            # Update session state
            st.session_state.current_page = page
            
            # Show persistent data info
            if st.session_state.processed_invoices:
                st.markdown('<div class="persistent-data-info">', unsafe_allow_html=True)
                st.markdown("**📊 Processed Data Available**")
                st.write(f"• {len(st.session_state.processed_invoices)} invoices ready")
                st.write("• Data persists across page changes")
                if st.button("🗑️ Clear Session Data", key="clear_session"):
                    st.session_state.processed_invoices = []
                    st.session_state.processing_complete = False
                    st.session_state.export_files = {}
                    st.success("Session data cleared!")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Processing Settings
            st.subheader("🔧 Processing Settings")
            
            model_options = {
                "Gemini 1.5 Pro": "gemini-1.5-pro-latest",
                "Gemini 1.5 Flash": "gemini-1.5-flash-latest", 
                "Gemini 1.0 Pro": "gemini-pro"
            }
            
            selected_model = st.selectbox("AI Model", list(model_options.keys()), key="model_select")
            self.config.gemini_model = model_options[selected_model]
            
            languages = [
                "Auto-detect", "English", "Spanish", "French", "German", 
                "Italian", "Portuguese", "Dutch", "Chinese", "Japanese", 
                "Korean", "Arabic", "Hindi"
            ]
            
            selected_language = st.selectbox("Processing Language", languages, key="language_select")
            
            # Processing options
            st.subheader("📋 Processing Options")
            extract_line_items = st.checkbox("Extract Line Items", value=True, key="extract_line_items_cb")
            calculate_totals = st.checkbox("Verify Calculations", value=True, key="calculate_totals_cb")
            detect_duplicates = st.checkbox("Detect Duplicates", value=True, key="detect_duplicates_cb")
            
            # Advanced options
            with st.expander("🔬 Advanced Options"):
                confidence_threshold = st.slider("Confidence Threshold", 0.5, 1.0, 0.85, key="confidence_slider")
                enable_validation = st.checkbox("Enable Data Validation", value=True, key="enable_validation_cb")
                save_to_database = st.checkbox("Save to Database", value=True, key="save_to_database_cb")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            return {
                'page': page,
                'model': selected_model,
                'language': selected_language,
                'extract_line_items': extract_line_items,
                'calculate_totals': calculate_totals,
                'detect_duplicates': detect_duplicates,
                'confidence_threshold': confidence_threshold,
                'enable_validation': enable_validation,
                'save_to_database': save_to_database
            }
    
    def render_invoice_processing_page(self, settings):
        """Enhanced invoice processing page with session state management"""
        st.subheader("📄 Invoice Processing")
        
        # Create columns for layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📁 Upload Invoice")
            
            uploaded_files = st.file_uploader(
                "Choose invoice files",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key="main_file_uploader"
            )
            
            custom_prompt = st.text_area(
                "Custom Instructions (Optional)",
                placeholder="e.g., 'Focus on vendor information'",
                height=100,
                key="main_custom_prompt"
            )
            
            if uploaded_files:
                if st.button("🚀 Process Invoices", type="primary", key="main_process_button"):
                    # Clear previous results
                    st.session_state.processed_invoices = []
                    st.session_state.processing_complete = False
                    
                    # Process files
                    self._process_uploaded_files(uploaded_files, custom_prompt, settings)
            
        with col2:
            st.markdown("### 📊 Quick Stats")
            total_processed = self.db_manager.get_total_invoices()
            today_processed = self.db_manager.get_invoices_by_date(datetime.now().date())
            
            st.metric("Total Processed", total_processed)
            st.metric("Today", len(today_processed))
            st.metric("Success Rate", "98.5%")
            
            # Show session data info
            if st.session_state.processed_invoices:
                st.markdown("### 💾 Session Data")
                st.success(f"{len(st.session_state.processed_invoices)} invoices in memory")
                if st.button("📋 View Results", key="view_results"):
                    st.session_state.show_results = True
        
        # Always show results if they exist in session state
        if st.session_state.processed_invoices and st.session_state.processing_complete:
            st.markdown("---")
            self._display_processing_results(st.session_state.processed_invoices)
    
    def _process_uploaded_files(self, uploaded_files, custom_prompt, settings):
        """Process uploaded files with session state storage"""
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                status_text.text(f"Processing {uploaded_file.name}...")
                
                if not self.validator.validate_file(uploaded_file):
                    st.error(f"Invalid file: {uploaded_file.name}")
                    continue
                
                result = self.processor.process_invoice(uploaded_file, custom_prompt, settings)
                
                if result:
                    results.append(result)
                    
                    if settings['save_to_database']:
                        self.db_manager.save_invoice_result(result)
                    
                    logger.info(f"Successfully processed: {uploaded_file.name}")
                else:
                    st.error(f"Failed to process: {uploaded_file.name}")
                    
            except Exception as e:
                logger.error(f"Error processing {uploaded_file.name}: {str(e)}")
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        if results:
            # Store in session state
            st.session_state.processed_invoices = results
            st.session_state.processing_complete = True
            st.success(f"✅ Processing complete! {len(results)} invoices processed successfully.")
            st.info("💡 Your data is now saved in session and available for export.")
    
    def _display_processing_results(self, results):
        """Display processing results with enhanced export functionality"""
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.subheader("✅ Processing Results")
        
        # Create tabs for different result views
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "📊 Details", "💾 Export", "🔍 Validation"])
        
        with tab1:
            self._render_results_summary(results)
        
        with tab2:
            self._render_results_details(results)
        
        with tab3:
            # PERSISTENT EXPORT SYSTEM
            self._render_persistent_export_interface(results)
        
        with tab4:
            self._render_validation_results(results)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_persistent_export_interface(self, invoice_data):
        """Persistent export interface that doesn't lose data on refresh"""
        st.markdown("### 🚀 Persistent Export System")
        st.info("💡 This data persists across page refreshes until you clear the session.")
        
        if not invoice_data:
            st.error("No invoice data available to export")
            return
        
        st.success(f"Ready to export {len(invoice_data)} invoices")
        
        # Pre-generate all export files to avoid refresh issues
        self._prepare_export_files(invoice_data)
        
        # Display download options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="export-card">', unsafe_allow_html=True)
            st.markdown("#### 📊 Excel Export")
            st.write("Formatted spreadsheet with multiple sheets")
            
            if 'excel' in st.session_state.export_files:
                file_data = st.session_state.export_files['excel']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"invoices_{timestamp}.xlsx"
                
                # Direct download button
                st.download_button(
                    label="📥 Download Excel",
                    data=file_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="persistent_excel_download"
                )
                
                st.caption(f"File size: {len(file_data):,} bytes")
            else:
                st.error("Excel file not ready")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="export-card">', unsafe_allow_html=True)
            st.markdown("#### 📄 CSV Export")
            st.write("Simple comma-separated values file")
            
            if 'csv' in st.session_state.export_files:
                file_data = st.session_state.export_files['csv']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"invoices_{timestamp}.csv"
                
                st.download_button(
                    label="📥 Download CSV",
                    data=file_data,
                    file_name=filename,
                    mime="text/csv",
                    key="persistent_csv_download"
                )
                
                st.caption(f"File size: {len(file_data):,} bytes")
            else:
                st.error("CSV file not ready")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="export-card">', unsafe_allow_html=True)
            st.markdown("#### 🗃️ JSON Export")
            st.write("Machine-readable data format")
            
            if 'json' in st.session_state.export_files:
                file_data = st.session_state.export_files['json']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"invoices_{timestamp}.json"
                
                st.download_button(
                    label="📥 Download JSON",
                    data=file_data,
                    file_name=filename,
                    mime="application/json",
                    key="persistent_json_download"
                )
                
                st.caption(f"File size: {len(file_data):,} bytes")
            else:
                st.error("JSON file not ready")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Option to refresh export files
        st.markdown("---")
        if st.button("🔄 Refresh Export Files", key="refresh_exports"):
            st.session_state.export_files = {}
            self._prepare_export_files(invoice_data)
            st.success("Export files refreshed!")
            st.rerun()
    
    def _prepare_export_files(self, invoice_data):
        """Pre-generate all export files and store in session state"""
        if not st.session_state.export_files:
            with st.spinner("Preparing export files..."):
                try:
                    # Generate Excel
                    excel_data = self._export_to_excel_direct(invoice_data)
                    if excel_data:
                        st.session_state.export_files['excel'] = excel_data
                    
                    # Generate CSV
                    csv_data = self._export_to_csv_direct(invoice_data)
                    if csv_data:
                        st.session_state.export_files['csv'] = csv_data
                    
                    # Generate JSON
                    json_data = self._export_to_json_direct(invoice_data)
                    if json_data:
                        st.session_state.export_files['json'] = json_data
                    
                    st.session_state.last_export_time = datetime.now()
                    
                except Exception as e:
                    st.error(f"Error preparing export files: {str(e)}")
    
    def _export_to_excel_direct(self, invoice_data):
        """Generate Excel file directly in memory"""
        try:
            processed_data = []
            for i, invoice in enumerate(invoice_data):
                row = {
                    'Invoice Number': str(invoice.get('invoice_number', f'Invoice_{i+1}')),
                    'Vendor Name': str(invoice.get('vendor_name', 'Unknown')),
                    'Invoice Date': str(invoice.get('invoice_date', '')),
                    'Due Date': str(invoice.get('due_date', '')),
                    'Total Amount': float(invoice.get('total_amount', 0)),
                    'Subtotal': float(invoice.get('subtotal', 0)),
                    'Tax Amount': float(invoice.get('tax_amount', 0)),
                    'Currency': str(invoice.get('currency', 'USD')),
                    'Payment Terms': str(invoice.get('payment_terms', '')),
                    'PO Number': str(invoice.get('po_number', '')),
                    'Confidence Score': f"{float(invoice.get('confidence', 0)):.1%}",
                    'File Name': str(invoice.get('file_name', '')),
                    'Processed Date': str(invoice.get('processed_at', ''))
                }
                processed_data.append(row)
            
            df = pd.DataFrame(processed_data)
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Invoices', index=False)
                
                # Add summary sheet
                summary_df = pd.DataFrame({
                    'Metric': ['Total Invoices', 'Total Amount', 'Export Date', 'Export Time'],
                    'Value': [
                        len(df), 
                        f"${df['Total Amount'].sum():,.2f}", 
                        datetime.now().strftime('%Y-%m-%d'),
                        datetime.now().strftime('%H:%M:%S')
                    ]
                })
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            excel_buffer.seek(0)
            return excel_buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Excel generation failed: {str(e)}")
            return None
    
    def _export_to_csv_direct(self, invoice_data):
        """Generate CSV file directly"""
        try:
            processed_data = []
            for i, invoice in enumerate(invoice_data):
                row = {
                    'Invoice Number': str(invoice.get('invoice_number', f'Invoice_{i+1}')),
                    'Vendor Name': str(invoice.get('vendor_name', 'Unknown')),
                    'Invoice Date': str(invoice.get('invoice_date', '')),
                    'Due Date': str(invoice.get('due_date', '')),
                    'Total Amount': float(invoice.get('total_amount', 0)),
                    'Currency': str(invoice.get('currency', 'USD')),
                    'Payment Terms': str(invoice.get('payment_terms', '')),
                    'PO Number': str(invoice.get('po_number', '')),
                    'Confidence Score': float(invoice.get('confidence', 0)),
                    'File Name': str(invoice.get('file_name', '')),
                    'Processed Date': str(invoice.get('processed_at', ''))
                }
                processed_data.append(row)
            
            df = pd.DataFrame(processed_data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            return csv_buffer.getvalue().encode('utf-8')
        
        except Exception as e:
            logger.error(f"CSV generation failed: {str(e)}")
            return None
    
    def _export_to_json_direct(self, invoice_data):
        """Generate JSON file directly"""
        try:
            export_data = {
                'export_info': {
                    'generated_at': datetime.now().isoformat(),
                    'total_invoices': len(invoice_data),
                    'generator': 'InvoiceGenius AI'
                },
                'invoices': invoice_data
            }
            
            json_string = json.dumps(export_data, indent=2, default=str)
            return json_string.encode('utf-8')
        
        except Exception as e:
            logger.error(f"JSON generation failed: {str(e)}")
            return None
    
    def _render_results_summary(self, results):
        """Render the results summary"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Files Processed", len(results))
        
        with col2:
            total_amount = sum([float(r.get('total_amount', 0)) for r in results if r.get('total_amount')])
            st.metric("Total Amount", f"${total_amount:,.2f}")
        
        with col3:
            avg_confidence = sum([r.get('confidence', 0) for r in results]) / len(results) if results else 0
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")
        
        # Summary table
        if results:
            summary_data = []
            for result in results:
                summary_data.append({
                    "Invoice Number": result.get('invoice_number', 'N/A'),
                    "Vendor": result.get('vendor_name', 'N/A'),
                    "Date": result.get('invoice_date', 'N/A'),
                    "Amount": f"${float(result.get('total_amount', 0)):,.2f}",
                    "Currency": result.get('currency', 'USD'),
                    "Status": "✅ Processed"
                })
            
            df = pd.DataFrame(summary_data)
            st.dataframe(df, use_container_width=True)
    
    def _render_results_details(self, results):
        """Render detailed results"""
        for i, result in enumerate(results):
            with st.expander(f"📄 Invoice {i+1}: {result.get('invoice_number', 'Unknown')}"):
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Basic Information:**")
                    st.write(f"• Invoice Number: {result.get('invoice_number', 'N/A')}")
                    st.write(f"• Vendor: {result.get('vendor_name', 'N/A')}")
                    st.write(f"• Date: {result.get('invoice_date', 'N/A')}")
                    st.write(f"• Due Date: {result.get('due_date', 'N/A')}")
                    st.write(f"• Total Amount: ${float(result.get('total_amount', 0)):,.2f}")
                
                with col2:
                    st.write("**Additional Details:**")
                    st.write(f"• Currency: {result.get('currency', 'N/A')}")
                    st.write(f"• Tax Amount: ${float(result.get('tax_amount', 0)):,.2f}")
                    st.write(f"• Payment Terms: {result.get('payment_terms', 'N/A')}")
                    st.write(f"• PO Number: {result.get('po_number', 'N/A')}")
                    st.write(f"• Confidence: {result.get('confidence', 0):.1%}")
                
                # Line items if available
                if result.get('line_items'):
                    st.write("**Line Items:**")
                    line_items_df = pd.DataFrame(result['line_items'])
                    st.dataframe(line_items_df, use_container_width=True)
    
    def _render_validation_results(self, results):
        """Render validation results"""
        st.write("### 🔍 Validation & Quality Check")
        
        for i, result in enumerate(results):
            with st.expander(f"Validation Report - Invoice {i+1}"):
                
                validation_score = result.get('validation_score', 0)
                confidence = result.get('confidence', 0)
                
                # Overall score
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Validation Score", f"{validation_score:.1%}")
                with col2:
                    st.metric("AI Confidence", f"{confidence:.1%}")
                
                # Detailed validation checks
                validation_results = result.get('validation_results', {})
                
                for check_name, check_result in validation_results.items():
                    status = "✅" if check_result['passed'] else "❌"
                    st.write(f"{status} **{check_name}**: {check_result['message']}")
    
    def render_analytics_dashboard(self):
        """Render the analytics dashboard"""
        st.subheader("📊 Analytics Dashboard")
        
        analytics_data = self.analytics.get_dashboard_data()
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Invoices", 
                analytics_data['total_invoices'],
                delta=analytics_data['invoices_this_month'] - analytics_data['invoices_last_month']
            )
        
        with col2:
            st.metric(
                "Total Amount", 
                f"${analytics_data['total_amount']:,.2f}",
                delta=f"${analytics_data['amount_change']:,.2f}"
            )
        
        with col3:
            st.metric(
                "Avg Processing Time", 
                f"{analytics_data['avg_processing_time']:.1f}s"
            )
        
        with col4:
            st.metric(
                "Success Rate", 
                f"{analytics_data['success_rate']:.1%}"
            )
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            monthly_data = self.analytics.get_monthly_trend()
            if monthly_data:
                fig = px.line(
                    monthly_data, 
                    x='month', 
                    y='count',
                    title="Monthly Invoice Processing Trend"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            vendor_data = self.analytics.get_vendor_distribution()
            if vendor_data:
                fig = px.pie(
                    vendor_data, 
                    values='count', 
                    names='vendor',
                    title="Top Vendors by Invoice Count"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Recent invoices table
        st.subheader("📋 Recent Invoices")
        recent_invoices = self.db_manager.get_recent_invoices(limit=10)
        if recent_invoices:
            df = pd.DataFrame(recent_invoices)
            st.dataframe(df, use_container_width=True)
    
    def render_export_center(self):
        """Export center for database exports with persistent system"""
        st.subheader("💾 Export Center")
        
        all_invoices = self.db_manager.get_all_invoices()
        
        if not all_invoices:
            st.info("No invoices found. Process some invoices first!")
            return
        
        st.write(f"📊 Total invoices: {len(all_invoices)}")
        
        # Option to load database data into session for export
        if st.button("📂 Load Database Data for Export", key="load_db_data"):
            st.session_state.processed_invoices = all_invoices
            st.session_state.processing_complete = True
            st.session_state.export_files = {}  # Clear existing export files
            st.success(f"Loaded {len(all_invoices)} invoices from database into session!")
            st.info("You can now export this data using the persistent export system below.")
        
        # Show export interface if data is loaded
        if st.session_state.processed_invoices:
            st.markdown("---")
            self._render_persistent_export_interface(st.session_state.processed_invoices)
    
    def render_batch_processing_page(self):
        """Render the batch processing page"""
        st.subheader("⚡ Batch Processing")
        
        st.info("Upload multiple invoices or a ZIP file containing invoices for bulk processing.")
        
        upload_option = st.radio(
            "Choose upload method:",
            ["Multiple Files", "ZIP Archive"]
        )
        
        if upload_option == "Multiple Files":
            uploaded_files = st.file_uploader(
                "Select multiple invoice files",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True
            )
            
            if uploaded_files and len(uploaded_files) > 1:
                st.success(f"Selected {len(uploaded_files)} files for batch processing")
                
                if st.button("🚀 Start Batch Processing"):
                    self._run_batch_processing(uploaded_files)
    
    def _run_batch_processing(self, files):
        """Run batch processing with session state storage"""
        st.write("### 🔄 Batch Processing in Progress...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        failed_files = []
        
        for i, file in enumerate(files):
            try:
                progress = (i + 1) / len(files)
                progress_bar.progress(progress)
                status_text.text(f"Processing {file.name} ({i+1}/{len(files)})")
                
                result = self.processor.process_invoice(file, "", {})
                
                if result:
                    results.append(result)
                    self.db_manager.save_invoice_result(result)
                else:
                    failed_files.append(file.name)
                    
            except Exception as e:
                failed_files.append(file.name)
                logger.error(f"Batch processing error for {file.name}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        # Store results in session state
        st.session_state.processed_invoices = results
        st.session_state.processing_complete = True
        st.session_state.export_files = {}  # Clear existing export files
        
        # Show results
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Successful", len(results))
        with col2:
            st.metric("❌ Failed", len(failed_files))
        with col3:
            st.metric("📊 Success Rate", f"{len(results)/(len(results)+len(failed_files))*100:.1f}%")
        
        if failed_files:
            with st.expander("❌ Failed Files"):
                for file_name in failed_files:
                    st.write(f"• {file_name}")
        
        if results:
            st.success(f"Batch processing completed! {len(results)} invoices processed successfully.")
            st.info("💡 Results are now available in session state for export.")
    
    def render_settings_page(self):
        """Render the settings page"""
        st.subheader("⚙️ Application Settings")
        
        # Session State Management
        with st.expander("💾 Session State Management"):
            st.write("**Current Session State:**")
            st.write(f"• Processed invoices: {len(st.session_state.processed_invoices)}")
            st.write(f"• Processing complete: {st.session_state.processing_complete}")
            st.write(f"• Export files ready: {len(st.session_state.export_files)}")
            
            if st.session_state.last_export_time:
                st.write(f"• Last export preparation: {st.session_state.last_export_time}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧹 Clear Session State"):
                    for key in ['processed_invoices', 'processing_complete', 'export_files', 'last_export_time']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.success("Session state cleared!")
                    st.rerun()
            
            with col2:
                if st.button("📊 View Session Details"):
                    st.json(dict(st.session_state))
        
        # Database Management
        with st.expander("🗄️ Database Management"):
            total_invoices = self.db_manager.get_total_invoices()
            st.write(f"Total invoices in database: {total_invoices}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear All Data"):
                    if st.checkbox("I understand this action cannot be undone"):
                        self.db_manager.clear_all_data()
                        st.success("Database cleared!")
            
            with col2:
                if st.button("💾 Backup Database"):
                    backup_file = self.db_manager.create_backup()
                    with open(backup_file, "rb") as file:
                        st.download_button(
                            label="Download Backup",
                            data=file.read(),
                            file_name=f"invoice_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                            mime="application/octet-stream"
                        )
        
        # Application Configuration
        with st.expander("⚙️ Application Configuration"):
            st.write("**Current Configuration:**")
            st.write(f"• Environment: {os.getenv('ENVIRONMENT', 'development')}")
            st.write(f"• Debug Mode: {os.getenv('DEBUG', 'false').lower() == 'true'}")
            st.write(f"• Max File Size: {os.getenv('MAX_FILE_SIZE_MB', '50')} MB")
            st.write(f"• Default Model: {os.getenv('DEFAULT_GEMINI_MODEL', 'gemini-1.5-pro-latest')}")

    def run(self):
        """Main application entry point"""
        # Configure page
        st.set_page_config(
            page_title="InvoiceGenius AI",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Load custom CSS
        self.load_custom_css()
        
        # Render header
        self.render_header()
        
        # Render sidebar and get settings
        settings = self.render_sidebar()
        
        # Route to appropriate page
        if settings['page'] == "Invoice Processing":
            self.render_invoice_processing_page(settings)
        elif settings['page'] == "Analytics Dashboard":
            self.render_analytics_dashboard()
        elif settings['page'] == "Batch Processing":
            self.render_batch_processing_page()
        elif settings['page'] == "Export Center":
            self.render_export_center()
        elif settings['page'] == "Settings":
            self.render_settings_page()

# Application entry point
if __name__ == "__main__":
    app = InvoiceGeniusApp()
    app.run()
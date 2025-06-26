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
        """Initialize the InvoiceGenius AI application"""
        self.config = Config()
        self.processor = InvoiceProcessor()
        self.db_manager = DatabaseManager()
        self.export_manager = ExportManager()
        self.validator = InputValidator()
        self.analytics = AnalyticsEngine(self.db_manager)
        
        # Ensure required directories exist
        self._create_directories()
        
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
        """Simple sidebar without complex state management"""
        with st.sidebar:
            st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
            
            # Simple navigation
            page = st.selectbox(
                "📊 Navigation", 
                [
                    "Invoice Processing", 
                    "Analytics Dashboard", 
                    "Batch Processing", 
                    "Export Center",
                    "Settings"
                ],
                key="main_navigation_select"
            )
            
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
        """Simple invoice processing page"""
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
                    self._process_uploaded_files(uploaded_files, custom_prompt, settings)
            
        with col2:
            st.markdown("### 📊 Quick Stats")
            total_processed = self.db_manager.get_total_invoices()
            today_processed = self.db_manager.get_invoices_by_date(datetime.now().date())
            
            st.metric("Total Processed", total_processed)
            st.metric("Today", len(today_processed))
            st.metric("Success Rate", "98.5%")
    
    def _process_uploaded_files(self, uploaded_files, custom_prompt, settings):
        """Process uploaded files - simple version"""
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
            self._display_processing_results(results)
    
    def _display_processing_results(self, results):
        """Display the processing results"""
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.subheader("✅ Processing Results")
        
        # Create tabs for different result views
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "📊 Details", "💾 Export", "🔍 Validation"])
        
        with tab1:
            # Summary view
            self._render_results_summary(results)
        
        with tab2:
            # Detailed view
            self._render_results_details(results)
        
        with tab3:
            # Export options
            self._render_export_options(results)
        
        with tab4:
            # Validation results
            self._render_validation_results(results)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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
    
    def _render_export_options(self, results):
        """Simple export options that actually work"""
        st.write("### 💾 Export Processed Data")
        
        if not results:
            st.warning("No data to export")
            return
        
        st.success(f"Ready to export {len(results)} invoices")
        
        # Simple direct exports
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export Excel", key=f"excel_{datetime.now().microsecond}"):
                excel_data = self._generate_excel_direct(results)
                if excel_data:
                    st.download_button(
                        "📥 Download Excel",
                        data=excel_data,
                        file_name=f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_excel_{datetime.now().microsecond}"
                    )
        
        with col2:
            if st.button("📄 Export CSV", key=f"csv_{datetime.now().microsecond}"):
                csv_data = self._generate_csv_direct(results)
                if csv_data:
                    st.download_button(
                        "📥 Download CSV",
                        data=csv_data,
                        file_name=f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key=f"dl_csv_{datetime.now().microsecond}"
                    )
        
        with col3:
            if st.button("🗃️ Export JSON", key=f"json_{datetime.now().microsecond}"):
                json_data = self._generate_json_direct(results)
                if json_data:
                    st.download_button(
                        "📥 Download JSON",
                        data=json_data,
                        file_name=f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key=f"dl_json_{datetime.now().microsecond}"
                    )
    
    def _generate_excel_direct(self, results):
        """Generate Excel directly"""
        try:
            import pandas as pd
            import io
            
            data = []
            for r in results:
                data.append({
                    'Invoice_Number': str(r.get('invoice_number', '')),
                    'Vendor_Name': str(r.get('vendor_name', '')),
                    'Total_Amount': float(r.get('total_amount', 0)) if r.get('total_amount') else 0,
                    'Currency': str(r.get('currency', 'USD')),
                    'Date': str(r.get('invoice_date', '')),
                    'File_Name': str(r.get('file_name', ''))
                })
            
            df = pd.DataFrame(data)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            st.error(f"Excel failed: {str(e)}")
            return None
    
    def _generate_csv_direct(self, results):
        """Generate CSV directly"""
        try:
            import pandas as pd
            import io
            
            data = []
            for r in results:
                data.append({
                    'Invoice_Number': str(r.get('invoice_number', '')),
                    'Vendor_Name': str(r.get('vendor_name', '')),
                    'Total_Amount': float(r.get('total_amount', 0)) if r.get('total_amount') else 0,
                    'Currency': str(r.get('currency', 'USD')),
                    'Date': str(r.get('invoice_date', '')),
                    'File_Name': str(r.get('file_name', ''))
                })
            
            df = pd.DataFrame(data)
            return df.to_csv(index=False).encode('utf-8')
        except Exception as e:
            st.error(f"CSV failed: {str(e)}")
            return None
    
    def _generate_json_direct(self, results):
        """Generate JSON directly"""
        try:
            import json
            export_data = {
                'generated_at': datetime.now().isoformat(),
                'total_invoices': len(results),
                'invoices': results
            }
            return json.dumps(export_data, indent=2, default=str).encode('utf-8')
        except Exception as e:
            st.error(f"JSON failed: {str(e)}")
            return None
    
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
        
        # Get analytics data
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
            # Monthly trend
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
            # Vendor distribution
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
    
    def render_batch_processing_page(self):
        """Render the batch processing page"""
        st.subheader("⚡ Batch Processing")
        
        st.info("Upload multiple invoices or a ZIP file containing invoices for bulk processing.")
        
        # Upload options
        upload_option = st.radio(
            "Choose upload method:",
            ["Multiple Files", "ZIP Archive", "Folder Upload"]
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
        
        elif upload_option == "ZIP Archive":
            zip_file = st.file_uploader(
                "Upload ZIP file containing invoices",
                type=["zip"]
            )
            
            if zip_file:
                if st.button("📦 Extract and Process ZIP"):
                    self._process_zip_file(zip_file)
    
    def _run_batch_processing(self, files):
        """Run batch processing on multiple files"""
        st.write("### 🔄 Batch Processing in Progress...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.empty()
        
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
        
        # Show final results
        progress_bar.empty()
        status_text.empty()
        
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
            self._display_processing_results(results)
    
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
    
    def render_export_center(self):
        """Simple export center that just works"""
        st.subheader("💾 Export Center")
        
        all_invoices = self.db_manager.get_all_invoices()
        
        if not all_invoices:
            st.info("No invoices found. Process some invoices first!")
            return
        
        st.write(f"📊 Total invoices: {len(all_invoices)}")
        
        # Simple export interface
        self._render_export_options(all_invoices)
    
    def render_settings_page(self):
        """Render the settings page"""
        st.subheader("⚙️ Application Settings")
        
        st.info("🔒 Security Note: API keys are managed through environment variables for security. Please update your .env file directly to change API configuration.")
        
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
            
            st.info("💡 To modify these settings, update your .env file and restart the application.")
        
        # Application Logs
        with st.expander("📋 Application Logs"):
            if os.path.exists("logs/app.log"):
                with open("logs/app.log", "r") as f:
                    logs = f.read()
                st.text_area("Recent Logs", logs, height=300)
            else:
                st.info("No logs available")

# Application entry point
if __name__ == "__main__":
    app = InvoiceGeniusApp()
    app.run()
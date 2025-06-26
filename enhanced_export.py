"""
Enhanced Export System for InvoiceGenius AI
==========================================

This enhanced version provides better error handling, user feedback, and
diagnostic capabilities to help identify and resolve export issues.

Think of this as adding a sophisticated monitoring system to our export
factory - we can now see exactly where things might be going wrong and
provide clear feedback to users about the process.
"""

import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any
import traceback

logger = logging.getLogger(__name__)

class EnhancedExportManager:
    """
    Enhanced export manager with comprehensive error handling and user feedback
    
    This version provides detailed diagnostics and graceful error handling
    to ensure users always understand what's happening during exports.
    """
    
    def __init__(self):
        """Initialize the enhanced export manager"""
        self.export_status = {
            'last_export_time': None,
            'last_export_type': None,
            'last_export_success': None,
            'last_error_message': None
        }
        logger.info("Enhanced export manager initialized")
    
    def export_to_excel_simple(self, invoice_data: List[Dict]) -> Optional[bytes]:
        """
        Create a simple Excel export with comprehensive error handling
        
        This function focuses on reliability over fancy formatting to ensure
        exports work consistently. Think of this as the "guaranteed delivery"
        version of our export system.
        """
        try:
            # Update status tracking
            self.export_status['last_export_time'] = datetime.now()
            self.export_status['last_export_type'] = 'Excel'
            
            # Step 1: Validate input data
            if not invoice_data:
                raise ValueError("No invoice data provided for export")
            
            logger.info(f"Starting Excel export for {len(invoice_data)} invoices")
            
            # Step 2: Prepare data for Excel
            processed_data = []
            for i, invoice in enumerate(invoice_data):
                try:
                    # Extract key fields with safe defaults
                    row = {
                        'Invoice Number': str(invoice.get('invoice_number', f'Invoice_{i+1}')),
                        'Vendor Name': str(invoice.get('vendor_name', 'Unknown Vendor')),
                        'Invoice Date': str(invoice.get('invoice_date', '')),
                        'Due Date': str(invoice.get('due_date', '')),
                        'Total Amount': self._safe_float(invoice.get('total_amount', 0)),
                        'Currency': str(invoice.get('currency', 'USD')),
                        'Payment Terms': str(invoice.get('payment_terms', '')),
                        'PO Number': str(invoice.get('po_number', '')),
                        'Confidence Score': f"{self._safe_float(invoice.get('confidence', 0)):.1%}",
                        'File Name': str(invoice.get('file_name', '')),
                        'Processed Date': str(invoice.get('processed_at', ''))
                    }
                    processed_data.append(row)
                    
                except Exception as e:
                    logger.warning(f"Error processing invoice {i}: {str(e)}")
                    # Continue with other invoices even if one fails
                    continue
            
            if not processed_data:
                raise ValueError("No valid invoice data could be processed")
            
            # Step 3: Create DataFrame
            df = pd.DataFrame(processed_data)
            logger.info(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
            
            # Step 4: Generate Excel file in memory
            excel_buffer = io.BytesIO()
            
            # Use xlsxwriter engine for better compatibility
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Invoice Data', index=False)
                
                # Add a summary sheet
                summary_data = {
                    'Metric': [
                        'Total Invoices',
                        'Total Amount',
                        'Average Amount',
                        'Export Date',
                        'Export Time'
                    ],
                    'Value': [
                        len(df),
                        f"${df['Total Amount'].sum():,.2f}",
                        f"${df['Total Amount'].mean():,.2f}",
                        datetime.now().strftime('%Y-%m-%d'),
                        datetime.now().strftime('%H:%M:%S')
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Step 5: Get the Excel file bytes
            excel_buffer.seek(0)
            excel_bytes = excel_buffer.getvalue()
            
            # Update success status
            self.export_status['last_export_success'] = True
            self.export_status['last_error_message'] = None
            
            logger.info(f"Excel export completed successfully. File size: {len(excel_bytes)} bytes")
            return excel_bytes
            
        except Exception as e:
            # Log the full error for debugging
            error_message = f"Excel export failed: {str(e)}"
            logger.error(error_message)
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Update failure status
            self.export_status['last_export_success'] = False
            self.export_status['last_error_message'] = error_message
            
            return None
    
    def export_to_json_simple(self, invoice_data: List[Dict]) -> Optional[bytes]:
        """
        Create a simple JSON export with error handling
        
        JSON exports are generally more reliable than complex formatted files
        because they have fewer dependencies and simpler structure.
        """
        try:
            # Update status tracking
            self.export_status['last_export_time'] = datetime.now()
            self.export_status['last_export_type'] = 'JSON'
            
            if not invoice_data:
                raise ValueError("No invoice data provided for export")
            
            logger.info(f"Starting JSON export for {len(invoice_data)} invoices")
            
            # Create export structure
            export_data = {
                'export_info': {
                    'generated_at': datetime.now().isoformat(),
                    'total_invoices': len(invoice_data),
                    'generator': 'InvoiceGenius AI',
                    'format_version': '1.0'
                },
                'invoices': invoice_data
            }
            
            # Convert to JSON bytes
            json_string = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
            json_bytes = json_string.encode('utf-8')
            
            # Update success status
            self.export_status['last_export_success'] = True
            self.export_status['last_error_message'] = None
            
            logger.info(f"JSON export completed successfully. File size: {len(json_bytes)} bytes")
            return json_bytes
            
        except Exception as e:
            error_message = f"JSON export failed: {str(e)}"
            logger.error(error_message)
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            self.export_status['last_export_success'] = False
            self.export_status['last_error_message'] = error_message
            
            return None
    
    def export_to_csv_simple(self, invoice_data: List[Dict]) -> Optional[bytes]:
        """
        Create a simple CSV export - the most universally compatible format
        
        CSV is often the most reliable export format because it has minimal
        dependencies and works with virtually any spreadsheet application.
        """
        try:
            # Update status tracking
            self.export_status['last_export_time'] = datetime.now()
            self.export_status['last_export_type'] = 'CSV'
            
            if not invoice_data:
                raise ValueError("No invoice data provided for export")
            
            logger.info(f"Starting CSV export for {len(invoice_data)} invoices")
            
            # Prepare data - same as Excel but simpler
            processed_data = []
            for i, invoice in enumerate(invoice_data):
                row = {
                    'Invoice Number': str(invoice.get('invoice_number', f'Invoice_{i+1}')),
                    'Vendor Name': str(invoice.get('vendor_name', 'Unknown Vendor')),
                    'Invoice Date': str(invoice.get('invoice_date', '')),
                    'Due Date': str(invoice.get('due_date', '')),
                    'Total Amount': self._safe_float(invoice.get('total_amount', 0)),
                    'Currency': str(invoice.get('currency', 'USD')),
                    'Payment Terms': str(invoice.get('payment_terms', '')),
                    'PO Number': str(invoice.get('po_number', '')),
                    'Confidence Score': self._safe_float(invoice.get('confidence', 0)),
                    'File Name': str(invoice.get('file_name', '')),
                    'Processed Date': str(invoice.get('processed_at', ''))
                }
                processed_data.append(row)
            
            # Create DataFrame and convert to CSV
            df = pd.DataFrame(processed_data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            
            # Convert to bytes
            csv_bytes = csv_buffer.getvalue().encode('utf-8')
            
            # Update success status
            self.export_status['last_export_success'] = True
            self.export_status['last_error_message'] = None
            
            logger.info(f"CSV export completed successfully. File size: {len(csv_bytes)} bytes")
            return csv_bytes
            
        except Exception as e:
            error_message = f"CSV export failed: {str(e)}"
            logger.error(error_message)
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            self.export_status['last_export_success'] = False
            self.export_status['last_error_message'] = error_message
            
            return None
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert any value to float with fallback"""
        try:
            if value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def get_export_status(self) -> Dict[str, Any]:
        """Get current export status for debugging"""
        return self.export_status.copy()
    
    def display_export_interface(self, invoice_data: List[Dict]):
        """
        Display an enhanced export interface with better user feedback
        
        This function creates a more robust export experience that provides
        clear feedback and handles errors gracefully.
        """
        st.subheader("📤 Export Invoice Data")
        
        if not invoice_data:
            st.warning("No invoice data available to export. Please process some invoices first.")
            return
        
        st.success(f"Ready to export {len(invoice_data)} invoices")
        
        # Create export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📊 Excel Export")
            st.write("Formatted spreadsheet with multiple sheets")
            if st.button("Export to Excel", key="excel_export", type="primary"):
                self._handle_export_with_feedback("Excel", invoice_data)
        
        with col2:
            st.markdown("### 📄 CSV Export")
            st.write("Simple comma-separated values file")
            if st.button("Export to CSV", key="csv_export", type="secondary"):
                self._handle_export_with_feedback("CSV", invoice_data)
        
        with col3:
            st.markdown("### 🗃️ JSON Export")
            st.write("Machine-readable data format")
            if st.button("Export to JSON", key="json_export", type="secondary"):
                self._handle_export_with_feedback("JSON", invoice_data)
        
        # Display export status
        self._display_export_status()
    
    def _handle_export_with_feedback(self, export_type: str, invoice_data: List[Dict]):
        """
        Handle export with comprehensive user feedback
        
        This function manages the entire export process while keeping the user
        informed about what's happening at each step.
        """
        # Show progress indicator
        with st.spinner(f"Generating {export_type} export..."):
            
            # Perform the export based on type
            if export_type == "Excel":
                file_bytes = self.export_to_excel_simple(invoice_data)
                file_extension = "xlsx"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                
            elif export_type == "CSV":
                file_bytes = self.export_to_csv_simple(invoice_data)
                file_extension = "csv"
                mime_type = "text/csv"
                
            elif export_type == "JSON":
                file_bytes = self.export_to_json_simple(invoice_data)
                file_extension = "json"
                mime_type = "application/json"
                
            else:
                st.error(f"Unknown export type: {export_type}")
                return
        
        # Handle the result
        if file_bytes:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"invoices_export_{timestamp}.{file_extension}"
            
            # Show success message
            st.success(f"✅ {export_type} export generated successfully!")
            
            # Provide download button
            st.download_button(
                label=f"📥 Download {export_type} File",
                data=file_bytes,
                file_name=filename,
                mime=mime_type,
                key=f"download_{export_type}_{timestamp}"
            )
            
            # Show file info
            st.info(f"File size: {len(file_bytes):,} bytes | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        else:
            # Show error message
            st.error(f"❌ {export_type} export failed!")
            
            # Show specific error if available
            if self.export_status['last_error_message']:
                st.error(f"Error details: {self.export_status['last_error_message']}")
            
            # Provide troubleshooting guidance
            with st.expander("🔧 Troubleshooting Tips"):
                st.write("If exports are failing, try these steps:")
                st.write("1. Check that you have processed invoices with valid data")
                st.write("2. Try a different export format (CSV is most reliable)")
                st.write("3. Check the application logs for detailed error information")
                st.write("4. Ensure you have sufficient disk space and memory")
                st.write("5. Try refreshing the page and processing invoices again")
    
    def _display_export_status(self):
        """Display current export status for debugging"""
        status = self.get_export_status()
        
        if status['last_export_time']:
            with st.expander("📊 Export Status"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Last Export:** {status['last_export_type']}")
                    st.write(f"**Time:** {status['last_export_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                with col2:
                    if status['last_export_success']:
                        st.write("**Status:** ✅ Success")
                    else:
                        st.write("**Status:** ❌ Failed")
                        if status['last_error_message']:
                            st.write(f"**Error:** {status['last_error_message']}")


def create_test_export_page():
    """
    Create a simple test page for export functionality
    
    This function allows you to test the export system with sample data
    to verify that everything is working correctly.
    """
    st.title("🧪 Export System Test")
    
    # Create sample invoice data for testing
    sample_data = [
        {
            'invoice_number': 'INV-001',
            'vendor_name': 'Test Vendor A',
            'invoice_date': '2024-06-01',
            'due_date': '2024-07-01',
            'total_amount': 1500.00,
            'currency': 'USD',
            'payment_terms': 'Net 30',
            'po_number': 'PO-12345',
            'confidence': 0.95,
            'file_name': 'test_invoice_1.pdf',
            'processed_at': datetime.now().isoformat()
        },
        {
            'invoice_number': 'INV-002',
            'vendor_name': 'Test Vendor B',
            'invoice_date': '2024-06-15',
            'due_date': '2024-07-15',
            'total_amount': 2750.50,
            'currency': 'USD',
            'payment_terms': 'Net 15',
            'po_number': 'PO-67890',
            'confidence': 0.87,
            'file_name': 'test_invoice_2.pdf',
            'processed_at': datetime.now().isoformat()
        }
    ]
    
    st.info("This page allows you to test the export functionality with sample data.")
    
    # Initialize export manager
    export_manager = EnhancedExportManager()
    
    # Display export interface
    export_manager.display_export_interface(sample_data)


# If running this file directly, show the test page
if __name__ == "__main__":
    create_test_export_page()
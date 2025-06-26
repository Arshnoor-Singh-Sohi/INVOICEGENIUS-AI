"""
Independent Export Solution for InvoiceGenius AI
===============================================

This solution creates a completely separate export interface that bypasses
all potential integration issues by running independently of the main app.

Think of this as a dedicated export station that connects directly to your
database and generates files without depending on any of the main app's
complex systems.
"""

import streamlit as st
import pandas as pd
import json
import sqlite3
import io
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add the project directory to Python path so we can import our config
project_root = Path(__file__).parent
sys.path.append(str(project_root))

class IndependentExporter:
    """
    A completely self-contained export system that connects directly
    to the database and generates files without any dependencies on
    the main application's systems.
    """
    
    def __init__(self):
        """Initialize the independent exporter"""
        # Get database path - this should match your main app's database location
        self.db_path = project_root / "data" / "invoices.db"
        self.export_stats = {
            'last_export_time': None,
            'files_generated': 0,
            'total_records_exported': 0
        }
    
    def get_database_connection(self):
        """Get direct connection to the invoice database"""
        try:
            if not self.db_path.exists():
                st.error(f"Database not found at {self.db_path}")
                st.info("Make sure you've processed some invoices in the main application first.")
                return None
            
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # This allows accessing columns by name
            return conn
        except Exception as e:
            st.error(f"Database connection failed: {str(e)}")
            return None
    
    def fetch_all_invoices(self):
        """Fetch all invoices directly from database"""
        conn = self.get_database_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.execute("""
                SELECT 
                    id, file_name, invoice_number, vendor_name, vendor_address,
                    invoice_date, due_date, total_amount, subtotal, tax_amount,
                    currency, payment_terms, po_number, confidence, 
                    validation_score, processing_time, ai_model, 
                    processor_version, created_at, updated_at, file_size, file_type
                FROM invoices 
                ORDER BY created_at DESC
            """)
            
            invoices = []
            for row in cursor.fetchall():
                # Convert row to dictionary
                invoice = dict(row)
                invoices.append(invoice)
            
            conn.close()
            return invoices
            
        except Exception as e:
            st.error(f"Failed to fetch invoices: {str(e)}")
            conn.close()
            return []
    
    def fetch_invoices_by_date_range(self, start_date, end_date):
        """Fetch invoices within a specific date range"""
        conn = self.get_database_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.execute("""
                SELECT 
                    id, file_name, invoice_number, vendor_name, vendor_address,
                    invoice_date, due_date, total_amount, subtotal, tax_amount,
                    currency, payment_terms, po_number, confidence, 
                    validation_score, processing_time, ai_model, 
                    processor_version, created_at, updated_at, file_size, file_type
                FROM invoices 
                WHERE DATE(created_at) BETWEEN ? AND ?
                ORDER BY created_at DESC
            """, (start_date, end_date))
            
            invoices = []
            for row in cursor.fetchall():
                invoice = dict(row)
                invoices.append(invoice)
            
            conn.close()
            return invoices
            
        except Exception as e:
            st.error(f"Failed to fetch invoices by date: {str(e)}")
            conn.close()
            return []
    
    def generate_excel_export(self, invoices):
        """Generate Excel file with comprehensive error handling"""
        try:
            if not invoices:
                return None, "No invoice data to export"
            
            # Prepare data for Excel - handle missing values gracefully
            excel_data = []
            for invoice in invoices:
                row = {
                    'ID': invoice.get('id', ''),
                    'Invoice Number': invoice.get('invoice_number', ''),
                    'Vendor Name': invoice.get('vendor_name', ''),
                    'Vendor Address': invoice.get('vendor_address', ''),
                    'Invoice Date': invoice.get('invoice_date', ''),
                    'Due Date': invoice.get('due_date', ''),
                    'Total Amount': self._safe_float(invoice.get('total_amount')),
                    'Subtotal': self._safe_float(invoice.get('subtotal')),
                    'Tax Amount': self._safe_float(invoice.get('tax_amount')),
                    'Currency': invoice.get('currency', 'USD'),
                    'Payment Terms': invoice.get('payment_terms', ''),
                    'PO Number': invoice.get('po_number', ''),
                    'Confidence Score': self._safe_float(invoice.get('confidence')),
                    'Validation Score': self._safe_float(invoice.get('validation_score')),
                    'Processing Time (s)': self._safe_float(invoice.get('processing_time')),
                    'AI Model': invoice.get('ai_model', ''),
                    'File Name': invoice.get('file_name', ''),
                    'File Size (bytes)': invoice.get('file_size', ''),
                    'File Type': invoice.get('file_type', ''),
                    'Processed Date': invoice.get('created_at', ''),
                    'Last Updated': invoice.get('updated_at', '')
                }
                excel_data.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(excel_data)
            
            # Generate Excel file in memory
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Invoice Data', index=False)
                
                # Summary sheet
                summary_data = {
                    'Metric': [
                        'Total Invoices',
                        'Total Amount',
                        'Average Amount',
                        'Unique Vendors',
                        'Date Range (First)',
                        'Date Range (Last)',
                        'Export Generated'
                    ],
                    'Value': [
                        len(df),
                        f"${df['Total Amount'].sum():,.2f}",
                        f"${df['Total Amount'].mean():,.2f}",
                        df['Vendor Name'].nunique(),
                        df['Invoice Date'].min() if not df['Invoice Date'].empty else 'N/A',
                        df['Invoice Date'].max() if not df['Invoice Date'].empty else 'N/A',
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            excel_buffer.seek(0)
            return excel_buffer.getvalue(), None
            
        except Exception as e:
            return None, f"Excel generation failed: {str(e)}"
    
    def generate_csv_export(self, invoices):
        """Generate CSV file"""
        try:
            if not invoices:
                return None, "No invoice data to export"
            
            # Prepare data for CSV
            csv_data = []
            for invoice in invoices:
                row = {
                    'ID': invoice.get('id', ''),
                    'Invoice_Number': invoice.get('invoice_number', ''),
                    'Vendor_Name': invoice.get('vendor_name', ''),
                    'Invoice_Date': invoice.get('invoice_date', ''),
                    'Due_Date': invoice.get('due_date', ''),
                    'Total_Amount': self._safe_float(invoice.get('total_amount')),
                    'Currency': invoice.get('currency', 'USD'),
                    'Payment_Terms': invoice.get('payment_terms', ''),
                    'PO_Number': invoice.get('po_number', ''),
                    'Confidence_Score': self._safe_float(invoice.get('confidence')),
                    'File_Name': invoice.get('file_name', ''),
                    'Processed_Date': invoice.get('created_at', '')
                }
                csv_data.append(row)
            
            # Create DataFrame and convert to CSV
            df = pd.DataFrame(csv_data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            
            return csv_buffer.getvalue().encode('utf-8'), None
            
        except Exception as e:
            return None, f"CSV generation failed: {str(e)}"
    
    def generate_json_export(self, invoices):
        """Generate JSON file"""
        try:
            if not invoices:
                return None, "No invoice data to export"
            
            # Create export structure
            export_data = {
                'export_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_invoices': len(invoices),
                    'export_type': 'full_database_export',
                    'generator': 'InvoiceGenius AI - Independent Exporter',
                    'version': '1.0'
                },
                'invoices': invoices
            }
            
            # Convert to JSON
            json_string = json.dumps(export_data, indent=2, default=str)
            return json_string.encode('utf-8'), None
            
        except Exception as e:
            return None, f"JSON generation failed: {str(e)}"
    
    def _safe_float(self, value):
        """Safely convert value to float"""
        try:
            if value is None or value == '':
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def update_export_stats(self, file_count, record_count):
        """Update export statistics"""
        self.export_stats['last_export_time'] = datetime.now()
        self.export_stats['files_generated'] += file_count
        self.export_stats['total_records_exported'] += record_count


def render_independent_export_interface():
    """
    Render the completely independent export interface
    
    This function creates a self-contained export system that operates
    independently of the main application's complexity.
    """
    
    st.title("📤 Independent Export System")
    st.markdown("---")
    
    # Initialize the independent exporter
    exporter = IndependentExporter()
    
    # Check database connectivity
    conn = exporter.get_database_connection()
    if not conn:
        return
    conn.close()
    
    # Fetch available data
    st.subheader("📊 Available Data")
    
    with st.spinner("Loading invoice data from database..."):
        all_invoices = exporter.fetch_all_invoices()
    
    if not all_invoices:
        st.warning("No invoices found in database. Process some invoices in the main application first.")
        return
    
    st.success(f"Found {len(all_invoices)} invoices in database")
    
    # Date range selection
    st.subheader("📅 Select Export Range")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date", 
            value=datetime.now().date() - timedelta(days=30),
            key="independent_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date", 
            value=datetime.now().date(),
            key="independent_end_date"
        )
    
    # Filter data by date range
    if st.button("Apply Date Filter", key="apply_filter"):
        with st.spinner("Filtering invoices by date range..."):
            filtered_invoices = exporter.fetch_invoices_by_date_range(start_date, end_date)
        
        if filtered_invoices:
            st.info(f"Found {len(filtered_invoices)} invoices in selected date range")
            st.session_state['filtered_invoices'] = filtered_invoices
        else:
            st.warning("No invoices found in selected date range")
            st.session_state['filtered_invoices'] = []
    
    # Use filtered data if available, otherwise use all data
    export_data = st.session_state.get('filtered_invoices', all_invoices)
    
    if not export_data:
        st.warning("No data available for export")
        return
    
    # Export interface
    st.subheader("🚀 Generate Exports")
    st.info(f"Ready to export {len(export_data)} invoices")
    
    # Create export columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📊 Excel Export")
        st.write("Comprehensive spreadsheet with multiple sheets")
        
        if st.button("Generate Excel", key="independent_excel"):
            with st.spinner("Creating Excel file..."):
                excel_data, error = exporter.generate_excel_export(export_data)
                
                if excel_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"invoices_export_{timestamp}.xlsx"
                    
                    st.download_button(
                        label="📥 Download Excel File",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_excel_{timestamp}"
                    )
                    
                    st.success("✅ Excel file generated successfully!")
                    st.info(f"File size: {len(excel_data):,} bytes")
                    
                    # Update stats
                    exporter.update_export_stats(1, len(export_data))
                    
                else:
                    st.error(f"❌ Excel export failed: {error}")
    
    with col2:
        st.markdown("#### 📄 CSV Export")
        st.write("Simple comma-separated values file")
        
        if st.button("Generate CSV", key="independent_csv"):
            with st.spinner("Creating CSV file..."):
                csv_data, error = exporter.generate_csv_export(export_data)
                
                if csv_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"invoices_export_{timestamp}.csv"
                    
                    st.download_button(
                        label="📥 Download CSV File",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        key=f"download_csv_{timestamp}"
                    )
                    
                    st.success("✅ CSV file generated successfully!")
                    st.info(f"File size: {len(csv_data):,} bytes")
                    
                    # Update stats
                    exporter.update_export_stats(1, len(export_data))
                    
                else:
                    st.error(f"❌ CSV export failed: {error}")
    
    with col3:
        st.markdown("#### 🗃️ JSON Export")
        st.write("Machine-readable data format")
        
        if st.button("Generate JSON", key="independent_json"):
            with st.spinner("Creating JSON file..."):
                json_data, error = exporter.generate_json_export(export_data)
                
                if json_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"invoices_export_{timestamp}.json"
                    
                    st.download_button(
                        label="📥 Download JSON File",
                        data=json_data,
                        file_name=filename,
                        mime="application/json",
                        key=f"download_json_{timestamp}"
                    )
                    
                    st.success("✅ JSON file generated successfully!")
                    st.info(f"File size: {len(json_data):,} bytes")
                    
                    # Update stats
                    exporter.update_export_stats(1, len(export_data))
                    
                else:
                    st.error(f"❌ JSON export failed: {error}")
    
    # Display export statistics
    st.markdown("---")
    st.subheader("📈 Export Statistics")
    
    stats = exporter.export_stats
    if stats['last_export_time']:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Files Generated", stats['files_generated'])
        with col2:
            st.metric("Records Exported", stats['total_records_exported'])
        with col3:
            st.metric("Last Export", stats['last_export_time'].strftime('%H:%M:%S'))
    
    # Data preview
    st.markdown("---")
    st.subheader("👀 Data Preview")
    
    if st.checkbox("Show data preview", key="show_preview"):
        # Display sample of data
        preview_data = export_data[:5]  # Show first 5 records
        
        for i, invoice in enumerate(preview_data):
            with st.expander(f"Invoice {i+1}: {invoice.get('invoice_number', 'Unknown')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Vendor:** {invoice.get('vendor_name', 'N/A')}")
                    st.write(f"**Date:** {invoice.get('invoice_date', 'N/A')}")
                    st.write(f"**Amount:** ${invoice.get('total_amount', 0):,.2f}")
                
                with col2:
                    st.write(f"**Currency:** {invoice.get('currency', 'N/A')}")
                    st.write(f"**Confidence:** {invoice.get('confidence', 0):.1%}")
                    st.write(f"**File:** {invoice.get('file_name', 'N/A')}")


# Main application function
def main():
    """Main function for the independent export application"""
    st.set_page_config(
        page_title="Independent Export System - InvoiceGenius AI",
        page_icon="📤",
        layout="wide"
    )
    
    render_independent_export_interface()


if __name__ == "__main__":
    main()
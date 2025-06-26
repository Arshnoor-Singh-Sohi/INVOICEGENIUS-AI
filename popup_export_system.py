"""
Popup Export System - Direct Working Solution
===========================================

This creates a popup-style export interface that works independently
of the main app's potential issues.
"""

import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
import base64

def create_download_link(file_data, filename, file_type):
    """Create a direct download link that bypasses Streamlit's download button issues"""
    if file_type == "excel":
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_type == "csv":
        mime_type = "text/csv"
    elif file_type == "json":
        mime_type = "application/json"
    else:
        mime_type = "application/octet-stream"
    
    b64_data = base64.b64encode(file_data).decode()
    
    # Create HTML download link
    download_link = f"""
    <a href="data:{mime_type};base64,{b64_data}" 
       download="{filename}" 
       style="display: inline-block; padding: 0.5rem 1rem; background-color: #0066cc; color: white; text-decoration: none; border-radius: 0.25rem; font-weight: bold;">
       📥 Click Here to Download {filename}
    </a>
    """
    return download_link

def export_to_excel_direct(invoice_data):
    """Generate Excel file directly in memory"""
    try:
        # Prepare data
        processed_data = []
        for i, invoice in enumerate(invoice_data):
            row = {
                'Invoice Number': str(invoice.get('invoice_number', f'Invoice_{i+1}')),
                'Vendor Name': str(invoice.get('vendor_name', 'Unknown')),
                'Invoice Date': str(invoice.get('invoice_date', '')),
                'Total Amount': float(invoice.get('total_amount', 0)),
                'Currency': str(invoice.get('currency', 'USD')),
                'File Name': str(invoice.get('file_name', '')),
                'Processed Date': str(invoice.get('processed_at', ''))
            }
            processed_data.append(row)
        
        # Create Excel in memory
        df = pd.DataFrame(processed_data)
        excel_buffer = io.BytesIO()
        
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Invoices', index=False)
            
            # Add summary
            summary_df = pd.DataFrame({
                'Metric': ['Total Invoices', 'Total Amount', 'Export Date'],
                'Value': [len(df), f"${df['Total Amount'].sum():,.2f}", datetime.now().strftime('%Y-%m-%d')]
            })
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        excel_buffer.seek(0)
        return excel_buffer.getvalue()
    
    except Exception as e:
        st.error(f"Excel generation failed: {str(e)}")
        return None

def export_to_csv_direct(invoice_data):
    """Generate CSV file directly"""
    try:
        processed_data = []
        for i, invoice in enumerate(invoice_data):
            row = {
                'Invoice Number': str(invoice.get('invoice_number', f'Invoice_{i+1}')),
                'Vendor Name': str(invoice.get('vendor_name', 'Unknown')),
                'Invoice Date': str(invoice.get('invoice_date', '')),
                'Total Amount': float(invoice.get('total_amount', 0)),
                'Currency': str(invoice.get('currency', 'USD')),
                'File Name': str(invoice.get('file_name', '')),
                'Processed Date': str(invoice.get('processed_at', ''))
            }
            processed_data.append(row)
        
        df = pd.DataFrame(processed_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue().encode('utf-8')
    
    except Exception as e:
        st.error(f"CSV generation failed: {str(e)}")
        return None

def export_to_json_direct(invoice_data):
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
        st.error(f"JSON generation failed: {str(e)}")
        return None

def render_popup_export_interface(invoice_data):
    """Render the popup export interface"""
    
    if not invoice_data:
        st.error("No invoice data available to export")
        return
    
    st.markdown("### 🚀 Direct Export System")
    st.success(f"Ready to export {len(invoice_data)} invoices")
    
    # Create three columns for export options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📊 Excel Export")
        if st.button("Generate Excel", key="direct_excel"):
            with st.spinner("Generating Excel..."):
                excel_data = export_to_excel_direct(invoice_data)
                
                if excel_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"invoices_{timestamp}.xlsx"
                    
                    download_link = create_download_link(excel_data, filename, "excel")
                    st.markdown(download_link, unsafe_allow_html=True)
                    st.success("✅ Excel file generated!")
    
    with col2:
        st.markdown("#### 📄 CSV Export")
        if st.button("Generate CSV", key="direct_csv"):
            with st.spinner("Generating CSV..."):
                csv_data = export_to_csv_direct(invoice_data)
                
                if csv_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"invoices_{timestamp}.csv"
                    
                    download_link = create_download_link(csv_data, filename, "csv")
                    st.markdown(download_link, unsafe_allow_html=True)
                    st.success("✅ CSV file generated!")
    
    with col3:
        st.markdown("#### 🗃️ JSON Export")
        if st.button("Generate JSON", key="direct_json"):
            with st.spinner("Generating JSON..."):
                json_data = export_to_json_direct(invoice_data)
                
                if json_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"invoices_{timestamp}.json"
                    
                    download_link = create_download_link(json_data, filename, "json")
                    st.markdown(download_link, unsafe_allow_html=True)
                    st.success("✅ JSON file generated!")
    
    # Alternative download method using st.download_button as backup
    st.markdown("---")
    st.markdown("#### 🔄 Alternative Download Method")
    st.info("If the above links don't work, try these download buttons:")
    
    # Generate all files and provide download buttons
    if st.button("Prepare All Downloads", key="prepare_all"):
        with st.spinner("Preparing all export formats..."):
            
            # Excel
            excel_data = export_to_excel_direct(invoice_data)
            if excel_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"invoices_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="backup_excel"
                )
            
            # CSV
            csv_data = export_to_csv_direct(invoice_data)
            if csv_data:
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"invoices_{timestamp}.csv",
                    mime="text/csv",
                    key="backup_csv"
                )
            
            # JSON
            json_data = export_to_json_direct(invoice_data)
            if json_data:
                st.download_button(
                    label="🗃️ Download JSON",
                    data=json_data,
                    file_name=f"invoices_{timestamp}.json",
                    mime="application/json",
                    key="backup_json"
                )

# Integration function for the main app
def add_popup_export_to_main_app():
    """
    Add this to your main app where you want export functionality
    
    Replace your existing export sections with:
    render_popup_export_interface(your_invoice_data)
    """
    
    # This is the integration code for your main app
    integration_code = '''
    # In your _render_export_options method, replace the content with:
    from popup_export_system import render_popup_export_interface
    
    def _render_export_options(self, results):
        """Render export options using popup system"""
        st.write("### 💾 Export Processed Data")
        render_popup_export_interface(results)
    '''
    
    return integration_code
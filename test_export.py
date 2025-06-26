import streamlit as st
from enhanced_export import EnhancedExportManager, create_test_export_page

# Set page configuration
st.set_page_config(
    page_title="Export System Test - InvoiceGenius AI",
    page_icon="🧪",
    layout="wide"
)

# Run the test page
create_test_export_page()
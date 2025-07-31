import streamlit as st
import traceback

try:
    # YOUR EXISTING CODE
    st.title("GSC Opportunity Finder")
    # ... load modules, files, run logic, etc.
except Exception as e:
    st.error("❌ Something went wrong:")
    st.code(traceback.format_exc())

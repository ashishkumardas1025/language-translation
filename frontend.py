import streamlit as st
import requests
import base64
import os
import json
import time
from typing import Optional

# App title and configuration
st.set_page_config(
    page_title="AI Document Translator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoint (assuming FastAPI backend is running)
API_URL = "http://localhost:8000/api"

# Helper functions
def get_base64_download_link(file_path, file_name):
    """Generate a download link for a file"""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">Download Translated Document</a>'

def display_document_preview(text, max_chars=2000):
    """Display a preview of the document text"""
    if len(text) > max_chars:
        return text[:max_chars] + "... (truncated)"
    return text

def call_api(endpoint, method="GET", data=None, files=None):
    """Call the backend API"""
    try:
        if method == "GET":
            response = requests.get(f"{API_URL}/{endpoint}")
        elif method == "POST":
            if files:
                response = requests.post(f"{API_URL}/{endpoint}", files=files)
            else:
                response = requests.post(f"{API_URL}/{endpoint}", json=data)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

# Initialize session state
if 'file_info' not in st.session_state:
    st.session_state.file_info = None
if 'translation_result' not in st.session_state:
    st.session_state.translation_result = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'is_translating' not in st.session_state:
    st.session_state.is_translating = False
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "translate"

# Custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f0ff;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e6f0ff;
    }
    .assistant-message {
        background-color: #f0f2f6;
    }
    .download-btn {
        background-color: #4CAF50;
        color: white;
        padding: 12px 20px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
        margin-top: 20px;
    }
    .download-btn:hover {
        background-color: #45a049;
    }
</style>
""", unsafe_allow_html=True)

# App header
st.title("🌐 AI Document Translation with Claude")
st.markdown("Translate documents from English to various languages using Claude 3.5 Sonnet AI")

# Create tabs
tabs = st.tabs(["📄 Translate Document", "💬 Chat with Documents"])

with tabs[0]:  # Translation Tab
    st.header("Document Translation")
    
    # Document upload section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader("Choose a document file", type=["txt", "docx"])
        
        # Target language selection
        language_options = ["French", "Spanish", "German", "Italian", "Portuguese", "Japanese", "Chinese", "Russian"]
        target_language = st.selectbox("Select target language", language_options)
        
        # Upload and translate buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            upload_btn = st.button("Upload Document", use_container_width=True)
        with col_btn2:
            translate_btn = st.button("Translate Document", use_container_width=True, 
                                      disabled=not st.session_state.file_info)
    
    with col2:
        st.subheader("Translation Progress")
        if st.session_state.is_translating:
            st.markdown("⏳ **Translation in progress...**")
            st.progress(0.75)
        elif st.session_state.translation_result:
            st.markdown("✅ **Translation completed!**")
            st.success("Document successfully translated")
            
            # Download button
            file_id = st.session_state.file_info.get("file_id")
            if file_id:
                download_info = call_api(f"download/{file_id}")
                if download_info and "file_path" in download_info:
                    file_path = download_info["file_path"]
                    file_name = f"translated_{os.path.basename(file_path)}"
                    st.markdown(get_base64_download_link(file_path, file_name), unsafe_allow_html=True)
        
        # Show file info if available
        if st.session_state.file_info:
            st.subheader("Document Information")
            st.write(f"**Filename:** {st.session_state.file_info.get('filename')}")
            file_size = len(st.session_state.file_info.get('text_content', ''))
            st.write(f"**Size:** {file_size} characters")
    
    # Process the upload
    if upload_btn and uploaded_file:
        st.session_state.translation_result = None
        
        # Create form data for API
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        
        with st.spinner("Uploading document..."):
            upload_result = call_api("upload", method="POST", files=files)
            
            if upload_result:
                st.session_state.file_info = upload_result
                st.success("Document uploaded successfully!")
                st.experimental_rerun()
    
    # Process translation
    if translate_btn and st.session_state.file_info:
        st.session_state.is_translating = True
        
        # Trigger translation
        with st.spinner("Translating document..."):
            file_id = st.session_state.file_info.get("file_id")
            translation_data = {
                "file_id": file_id,
                "target_language": target_language
            }
            
            translation_result = call_api("translate", method="POST", data=translation_data)
            
            if translation_result:
                st.session_state.translation_result = translation_result
                st.session_state.is_translating = False
                st.success("Translation completed!")
                st.experimental_rerun()
    
    # Display document text and translation
    if st.session_state.file_info or st.session_state.translation_result:
        st.subheader("Document Content")
        
        # Original and translated text in columns
        original_col, translated_col = st.columns(2)
        
        with original_col:
            st.markdown("**Original Text (English)**")
            if st.session_state.file_info:
                original_text = st.session_state.file_info.get("text_content", "")
                st.text_area("", display_document_preview(original_text), height=300)
        
        with translated_col:
            st.markdown(f"**Translated Text ({target_language})**")
            if st.session_state.translation_result:
                translated_text = st.session_state.translation_result.get("translated_text", "")
                st.text_area("", display_document_preview(translated_text), height=300)
            else:
                st.text_area("", "Translation will appear here...", height=300)
    
    # Display document analysis and quality check if available
    if st.session_state.translation_result:
        analysis_expander = st.expander("Document Analysis & Quality Check Details")
        
        with analysis_expander:
            document_analysis = st.session_state.translation_result.get("document_analysis", {})
            quality_review = st.session_state.translation_result.get("quality_review", {})
            
            # Document analysis section
            st.subheader("Document Analysis")
            if document_analysis:
                try:
                    for key, value in document_analysis.items():
                        if isinstance(value, dict):
                            st.write(f"**{key.replace('_', ' ').title()}**")
                            for sub_key, sub_value in value.items():

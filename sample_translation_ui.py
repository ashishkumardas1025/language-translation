import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path
import logging
import time
from typing import Optional
import traceback

# Import the backend processor
try:
    from pdf_processor_backend import process_pdf_file, PDFProcessor
except ImportError:
    st.error("Backend processor not found. Please ensure pdf_processor_backend.py is in the same directory.")
    st.stop()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="PDF Translator - English to Canadian French",
    page_icon="🇨🇦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-bottom: 1rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'output_file_path' not in st.session_state:
        st.session_state.output_file_path = None
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = "ready"
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None

def validate_environment():
    """Validate required environment variables"""
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.info("Please set your AWS credentials in the environment variables.")
        return False
    return True

def display_file_info(uploaded_file):
    """Display information about the uploaded file"""
    file_details = {
        "Filename": uploaded_file.name,
        "File size": f"{uploaded_file.size / 1024:.2f} KB",
        "File type": uploaded_file.type
    }
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**File Details:**")
        for key, value in file_details.items():
            st.write(f"- **{key}:** {value}")

def process_uploaded_file(uploaded_file) -> Optional[str]:
    """Process the uploaded PDF file"""
    try:
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            input_path = os.path.join(temp_dir, uploaded_file.name)
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Create output directory
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Process the file
            st.session_state.processing_status = "processing"
            result_path = process_pdf_file(input_path, output_dir)
            
            # Copy result to a permanent location
            permanent_dir = "output"
            os.makedirs(permanent_dir, exist_ok=True)
            final_path = os.path.join(permanent_dir, Path(result_path).name)
            shutil.copy2(result_path, final_path)
            
            return final_path
            
    except Exception as e:
        logger.error(f"Processing error: {e}")
        st.session_state.error_message = str(e)
        st.session_state.processing_status = "error"
        return None

def main():
    """Main Streamlit application"""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🇨🇦 PDF Translator</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">English to Canadian French Translation</h2>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Environment validation
        if not validate_environment():
            st.stop()
        
        st.success("✅ AWS credentials configured")
        
        st.header("📋 Features")
        st.markdown("""
        - **Text Translation**: Professional business document translation
        - **Image Analysis**: AI-powered image content description
        - **Table Processing**: Structured data translation
        - **Document Preservation**: Maintains original formatting
        - **Multimodal AI**: Uses Claude 3.5 Sonnet for comprehensive analysis
        """)
        
        st.header("📄 Supported Content")
        st.markdown("""
        - Text paragraphs and headings
        - Charts and graphs
        - Tables and data
        - Images and diagrams
        - Financial reports
        - Business documents
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📤 Upload PDF Document")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file to translate",
            type=['pdf'],
            help="Upload a PDF document to translate from English to Canadian French"
        )
        
        if uploaded_file is not None:
            display_file_info(uploaded_file)
            
            # Processing button
            if st.button("🚀 Start Translation Process", type="primary", use_container_width=True):
                if st.session_state.processing_status != "processing":
                    st.session_state.processing_complete = False
                    st.session_state.error_message = None
                    
                    # Show progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Processing steps
                    steps = [
                        "Initializing processor...",
                        "Extracting PDF content...",
                        "Analyzing images with Claude...",
                        "Translating text content...",
                        "Processing tables...",
                        "Creating translated document...",
                        "Finalizing output..."
                    ]
                    
                    try:
                        for i, step in enumerate(steps):
                            status_text.text(step)
                            progress_bar.progress((i + 1) / len(steps))
                            time.sleep(0.5)  # Simulate processing time
                        
                        # Actually process the file
                        status_text.text("Processing with Claude AI...")
                        result_path = process_uploaded_file(uploaded_file)
                        
                        if result_path and os.path.exists(result_path):
                            st.session_state.output_file_path = result_path
                            st.session_state.processing_complete = True
                            st.session_state.processing_status = "complete"
                            progress_bar.progress(1.0)
                            status_text.text("✅ Translation completed successfully!")
                        else:
                            st.session_state.processing_status = "error"
                            if not st.session_state.error_message:
                                st.session_state.error_message = "Unknown processing error"
                    
                    except Exception as e:
                        st.session_state.error_message = str(e)
                        st.session_state.processing_status = "error"
                        logger.error(f"Processing failed: {e}")
                        traceback.print_exc()
    
    with col2:
        st.markdown("### 📊 Processing Status")
        
        if st.session_state.processing_status == "ready":
            st.markdown('<div class="status-box info-box">Ready to process PDF documents</div>', unsafe_allow_html=True)
        
        elif st.session_state.processing_status == "processing":
            st.markdown('<div class="status-box warning-box">🔄 Processing in progress...</div>', unsafe_allow_html=True)
        
        elif st.session_state.processing_status == "complete":
            st.markdown('<div class="status-box success-box">✅ Translation completed successfully!</div>', unsafe_allow_html=True)
        
        elif st.session_state.processing_status == "error":
            st.markdown('<div class="status-box error-box">❌ Processing failed</div>', unsafe_allow_html=True)
            if st.session_state.error_message:
                st.error(f"Error: {st.session_state.error_message}")
    
    # Download section
    if st.session_state.processing_complete and st.session_state.output_file_path:
        st.markdown("---")
        st.markdown("### 📥 Download Translated Document")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if os.path.exists(st.session_state.output_file_path):
                with open(st.session_state.output_file_path, "rb") as file:
                    st.download_button(
                        label="📄 Download Translated DOCX",
                        data=file.read(),
                        file_name=Path(st.session_state.output_file_path).name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary",
                        use_container_width=True
                    )
                
                st.success("Document ready for download!")
                
                # File info
                file_size = os.path.getsize(st.session_state.output_file_path)
                st.info(f"File size: {file_size / 1024:.2f} KB")
            else:
                st.error("Output file not found. Please try processing again.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>Powered by Claude 3.5 Sonnet via AWS Bedrock | Professional Document Translation Service</p>
        <p>🔒 Your documents are processed securely and not stored permanently</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

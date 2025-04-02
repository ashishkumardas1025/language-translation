# app.py
import streamlit as st
import mammoth
import os
import docx
import tempfile
import base64
from io import BytesIO
from translation_functions import process_document

def extract_text_from_docx(file_path):
    """Extract text from a .docx file"""
    with open(file_path, "rb") as docx_file:
        result = mammoth.extract_raw_text(docx_file)
        return result.value

def extract_text_from_txt(file_path):
    """Extract text from a .txt file"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def create_download_link(content, filename, link_text):
    """Generate a download link for text content"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

def save_docx(text, filename):
    """Save text to a .docx file and create download link"""
    # Create a docx file
    doc = docx.Document()
    for paragraph in text.split('\n'):
        doc.add_paragraph(paragraph)
    
    # Save to BytesIO object
    tmp = BytesIO()
    doc.save(tmp)
    tmp.seek(0)
    
    # Create download link
    b64 = base64.b64encode(tmp.getvalue()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64}" download="{filename}">{filename}</a>'
    return href

def main():
    st.set_page_config(page_title="Document Translator", layout="wide")
    
    st.title("🌐 AI Document Translator")
    st.markdown("Upload documents (.txt, .docx) and translate them with AI")
    
    with st.sidebar:
        st.header("Translation Settings")
        target_language = st.selectbox(
            "Select Target Language",
            ["French", "Spanish", "German", "Italian", "Portuguese", "Chinese", "Japanese", "Korean", "Russian", "Arabic"]
        )
        
        st.divider()
        st.markdown("### About")
        st.markdown("""
        This app uses AI to translate documents while preserving:
        - Original formatting
        - Document structure
        - Technical terminology
        - Tone and style
        """)
    
    uploaded_file = st.file_uploader("Upload a document", type=["txt", "docx", "doc"])
    
    if uploaded_file is not None:
        # Create a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split(".")[-1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            temp_file_path = tmp.name
        
        # Extract text based on file type
        file_extension = uploaded_file.name.split(".")[-1].lower()
        if file_extension == "docx":
            text_content = extract_text_from_docx(temp_file_path)
        elif file_extension == "txt":
            text_content = extract_text_from_txt(temp_file_path)
        else:
            st.error("Unsupported file format. Please upload .txt or .docx files.")
            os.unlink(temp_file_path)
            return
        
        # Remove temp file
        os.unlink(temp_file_path)
        
        # Display original text
        st.subheader("Original Document")
        with st.expander("Show Original Content", expanded=True):
            st.text_area("Original Text", text_content, height=300)
        
        # Translation section
        st.subheader(f"Translation to {target_language}")
        
        # Start translation button
        if st.button("Translate Document"):
            with st.spinner(f"Translating document to {target_language}..."):
                # Progress tracking
                progress_bar = st.progress(0)
                
                # Step 1: Document analysis
                st.markdown("🔍 Analyzing document structure and content...")
                progress_bar.progress(25)
                
                # Step 2: Translation
                st.markdown("📝 Translating content...")
                progress_bar.progress(50)
                
                # Step 3: Quality check
                st.markdown("⚖️ Checking translation quality...")
                progress_bar.progress(75)
                
                # Step 4: Enhancements
                st.markdown("✨ Applying contextual enhancements...")
                progress_bar.progress(90)
                
                # Run the full translation process
                result = process_document(text_content, target_language)
                
                progress_bar.progress(100)
                st.success("Translation completed!")
                
                if "error" in result:
                    st.error(f"Error during {result.get('stage', 'translation')}: {result['error']}")
                else:
                    # Display translated text
                    st.text_area("Translated Text", result["translated_text"], height=300)
                    
                    # Download options
                    st.subheader("Download Options")
                    col1, col2 = st.columns(2)
                    
                    # Download as TXT
                    with col1:
                        txt_download = create_download_link(
                            result["translated_text"], 
                            f"{uploaded_file.name.split('.')[0]}_translated_{target_language}.txt",
                            "Download as TXT"
                        )
                        st.markdown(txt_download, unsafe_allow_html=True)
                    
                    # Download as DOCX
                    with col2:
                        docx_download = save_docx(
                            result["translated_text"],
                            f"{uploaded_file.name.split('.')[0]}_translated_{target_language}.docx"
                        )
                        st.markdown(docx_download, unsafe_allow_html=True)
                    
                    # Display document analysis if available
                    if "document_analysis" in result and result["document_analysis"]:
                        with st.expander("Document Analysis"):
                            st.json(result["document_analysis"])
                    
                    # Display quality review if available
                    if "quality_review" in result and result["quality_review"]:
                        with st.expander("Translation Quality Assessment"):
                            st.json(result["quality_review"])

if __name__ == "__main__":
    main()

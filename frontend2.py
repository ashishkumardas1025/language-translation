import streamlit as st
import pandas as pd
import os
from translation_agents import TranslationWorkflow  # Assuming your agents are in this module
from io import BytesIO

# Initialize translation workflow
workflow = TranslationWorkflow()

def process_file(uploaded_file, target_language="French"):
    """Reads file content and processes translation."""
    if uploaded_file is not None:
        file_extension = os.path.splitext(uploaded_file.name)[-1].lower()
        
        if file_extension == ".txt":
            text_content = uploaded_file.read().decode("utf-8")
        elif file_extension in [".docx", ".pdf"]:
            st.error("Only .txt files are supported currently.")
            return None, None
        else:
            st.error("Unsupported file type.")
            return None, None
        
        # Run the translation workflow
        result = workflow.process_document(text_content, target_language)
        return text_content, result.get("translated_text", "")
    
    return None, None

def download_file(text, filename="translated.txt"):
    """Creates a downloadable file."""
    buffer = BytesIO()
    buffer.write(text.encode("utf-8"))
    buffer.seek(0)
    return buffer

# Streamlit UI
st.title("EN to French Translation")

uploaded_file = st.file_uploader("Upload a text file", type=["txt"])
target_language = st.selectbox("Target Language", ["French"], index=0)

if uploaded_file:
    original_text, translated_text = process_file(uploaded_file, target_language)
    
    if original_text and translated_text:
        tab1, tab2 = st.tabs(["Original Text", "Translated Text"])
        with tab1:
            st.text_area("Original Text", original_text, height=300)
        with tab2:
            st.text_area("Translated Text", translated_text, height=300)
        
        # Provide download option
        st.download_button(
            label="Download Translation",
            data=download_file(translated_text),
            file_name="translated.txt",
            mime="text/plain"
        )

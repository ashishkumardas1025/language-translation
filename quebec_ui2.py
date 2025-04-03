# app.py
import streamlit as st
import mammoth
import os
import docx
import tempfile
import base64
from io import BytesIO
from quebec_translation import process_document_for_quebec_french

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

def calculate_keyword_accuracy(generated_text, reference_text):
    """Calculate keyword overlap between generated and reference translations"""
    # Convert to lowercase for comparison
    gen_lower = generated_text.lower()
    ref_lower = reference_text.lower()
    
    # Extract words (simplistic approach - could be improved)
    gen_words = set([w.strip('.,;:!?()[]{}"\'-') for w in gen_lower.split()])
    ref_words = set([w.strip('.,;:!?()[]{}"\'-') for w in ref_lower.split()])
    
    # Calculate overlap
    common_words = gen_words.intersection(ref_words)
    
    # Get important keywords (words longer than 5 chars might be more significant)
    important_keywords = [word for word in common_words if len(word) > 5]
    
    # Calculate accuracy
    if len(ref_words) > 0:
        overlap_percentage = (len(common_words) / len(ref_words)) * 100
    else:
        overlap_percentage = 0
        
    return {
        "overlap_percentage": round(overlap_percentage, 2),
        "common_words": len(common_words),
        "reference_words": len(ref_words),
        "important_keywords": important_keywords[:20]  # Limit to 20 important keywords
    }

def main():
    st.set_page_config(
        page_title="Quebec French Document Translator", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Quebec flag colors
    quebec_blue = "#095797"
    quebec_white = "#FFFFFF"
    
    st.markdown(
        f"""
        <style>
        .main-header {{
            color: {quebec_blue};
        }}
        .stProgress > div > div {{
            background-color: {quebec_blue};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("<h1 class='main-header'>🍁 AI Quebec French Document Translator</h1>", unsafe_allow_html=True)
    st.markdown("Upload documents (.txt, .docx) and translate them to authentic Quebec French")
    
    with st.sidebar:
        st.header("Translation Settings")
        
        st.markdown("### Quebec French Dialect Options")
        formality_level = st.select_slider(
            "Formality Level",
            options=["Informal (Joual)", "Semi-formal", "Formal/Professional"],
            value="Semi-formal"
        )
        
        quebec_region = st.selectbox(
            "Regional Dialect Preference",
            ["General Quebec French", "Montreal", "Quebec City", "Outaouais", "Saguenay-Lac-Saint-Jean"],
            index=0
        )
        
        preserve_options = st.multiselect(
            "Elements to Preserve/Adapt",
            ["Technical terminology", "Cultural references", "Idiomatic expressions", "Industry jargon"],
            default=["Technical terminology", "Cultural references"]
        )
        
        st.divider()
        
        st.markdown("### About")
        st.markdown("""
        This app uses AI to translate documents to authentic Quebec French while preserving:
        - Original formatting and document structure
        - Quebec French terminology and expressions
        - Cultural context adaptations for Quebec audiences
        - Technical terminology with Quebec French equivalents
        - Regional dialect nuances when applicable
        """)
        
        st.markdown("""
        <div style='background-color:#f0f2f6;padding:10px;border-radius:5px;margin-top:20px'>
        <h4>What is Quebec French?</h4>
        <p>Quebec French (français québécois) is the predominant variety of French spoken in Canada, 
        with its own distinct vocabulary, expressions, grammar patterns, and pronunciation. It differs 
        significantly from International French in many aspects.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main tabs
    tab1, tab2 = st.tabs(["Translate Document", "Validate Translation"])
    
    with tab1:
        uploaded_file = st.file_uploader("Upload a document", type=["txt", "docx", "doc"], key="source_doc")
        
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
            st.subheader("Quebec French Translation")
            
            # Custom parameters based on user selections
            custom_parameters = {
                "formality_level": formality_level,
                "quebec_region": quebec_region,
                "preserve_options": preserve_options
            }
            
            # Start translation button
            if st.button("Translate to Quebec French"):
                with st.spinner("Translating document to Quebec French..."):
                    # Progress tracking
                    progress_bar = st.progress(0)
                    
                    # Step 1: Document analysis
                    st.markdown("🔍 Analyzing document structure and content...")
                    progress_bar.progress(20)
                    
                    # Step 2: Quebec French glossary creation
                    st.markdown("📚 Creating Quebec French terminology glossary...")
                    progress_bar.progress(35)
                    
                    # Step 3: Translation
                    st.markdown("📝 Translating to Quebec French...")
                    progress_bar.progress(55)
                    
                    # Step 4: Quebec authenticity check
                    st.markdown("⚜️ Verifying Quebec French authenticity...")
                    progress_bar.progress(75)
                    
                    # Step 5: Regional adaptations
                    st.markdown("🍁 Adding regional Quebec French expressions...")
                    progress_bar.progress(90)
                    
                    # Run the full translation process
                    result = process_document_for_quebec_french(text_content)
                    
                    progress_bar.progress(100)
                    st.success("Quebec French translation completed!")
                    
                    if "error" in result:
                        st.error(f"Error during {result.get('stage', 'translation')}: {result['error']}")
                    else:
                        # Store the translation in session state for validation tab
                        st.session_state['translated_text'] = result["translated_text"]
                        st.session_state['original_text'] = text_content
                        st.session_state['filename'] = uploaded_file.name
                        
                        # Display translated text
                        st.text_area("Quebec French Translation", result["translated_text"], height=300)
                        
                        # Download options
                        st.subheader("Download Options")
                        col1, col2 = st.columns(2)
                        
                        # Download as TXT
                        with col1:
                            txt_download = create_download_link(
                                result["translated_text"], 
                                f"{uploaded_file.name.split('.')[0]}_quebec_french.txt",
                                "Download as TXT"
                            )
                            st.markdown(txt_download, unsafe_allow_html=True)
                        
                        # Download as DOCX
                        with col2:
                            docx_download = save_docx(
                                result["translated_text"],
                                f"{uploaded_file.name.split('.')[0]}_quebec_french.docx"
                            )
                            st.markdown(docx_download, unsafe_allow_html=True)
                        
                        # Quebec French specific insights
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            with st.expander("Quebec French Terminology Used"):
                                if "document_analysis" in result and result["document_analysis"]:
                                    if "quebec_terminology" in result["document_analysis"]:
                                        st.json(result["document_analysis"]["quebec_terminology"])
                                    else:
                                        st.write("No specific Quebec terminology analysis available.")
                                else:
                                    st.write("No terminology analysis available.")
                        
                        with col2:
                            with st.expander("Quebec French Authenticity Score"):
                                if "quality_review" in result and result["quality_review"]:
                                    if "quebec_french_authenticity" in result["quality_review"]:
                                        authenticity = result["quality_review"]["quebec_french_authenticity"]
                                        st.metric("Authenticity Score", f"{authenticity}/10")
                                        
                                        if isinstance(authenticity, (int, float)) or (isinstance(authenticity, str) and authenticity.isdigit()):
                                            auth_score = float(authenticity)
                                            if auth_score >= 8:
                                                st.success("Excellent Quebec French authenticity!")
                                            elif auth_score >= 6:
                                                st.info("Good Quebec French authenticity with some room for improvement.")
                                            else:
                                                st.warning("The translation may need more Quebec French expressions.")
                                    else:
                                        st.write("No authenticity score available.")
                                else:
                                    st.write("No quality review available.")
                        
                        # Display full document analysis if available
                        if "document_analysis" in result and result["document_analysis"]:
                            with st.expander("Document Analysis"):
                                st.json(result["document_analysis"])
                        
                        # Display quality review if available
                        if "quality_review" in result and result["quality_review"]:
                            with st.expander("Translation Quality Assessment"):
                                st.json(result["quality_review"])
                        
                        # Cultural adaptation notes
                        with st.expander("Cultural Adaptation Notes"):
                            if "quality_review" in result and result["quality_review"] and "cultural_adaptations_assessment" in result["quality_review"]:
                                st.write(result["quality_review"]["cultural_adaptations_assessment"])
                            else:
                                st.write("""
                                Cultural references have been adapted to be relevant to a Quebec audience. 
                                This includes considerations for Quebec history, values, and cultural touchpoints.
                                """)
                                
                        # Quebec French language tips
                        st.markdown("""
                        ### 💡 Quebec French Language Tips
                        
                        This translation uses authentic Quebec French expressions and terminology. Some key differences from International French include:
                        
                        - Different vocabulary choices unique to Quebec
                        - Contractions and speech patterns common in Quebec
                        - Cultural references adapted for Quebec audiences
                        - Technical terminology using Quebec industry standards
                        """)
    
    with tab2:
        st.subheader("Validate with Reference Quebec French")
        st.info("Upload a reference Quebec French document to compare with the AI translation")
        
        if 'translated_text' not in st.session_state:
            st.warning("Please translate a document first in the Translate Document tab")
        else:
            reference_file = st.file_uploader("Upload reference Quebec French document", type=["txt", "docx", "doc"], key="reference_doc")
            
            if reference_file is not None:
                # Create a temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix="." + reference_file.name.split(".")[-1]) as tmp:
                    tmp.write(reference_file.getvalue())
                    temp_file_path = tmp.name
                
                # Extract text based on file type
                file_extension = reference_file.name.split(".")[-1].lower()
                if file_extension == "docx":
                    reference_text = extract_text_from_docx(temp_file_path)
                elif file_extension == "txt":
                    reference_text = extract_text_from_txt(temp_file_path)
                else:
                    st.error("Unsupported file format. Please upload .txt or .docx files.")
                    os.unlink(temp_file_path)
                    return
                
                # Remove temp file
                os.unlink(temp_file_path)
                
                # Display side by side comparison
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("AI Quebec French Translation")
                    st.text_area("AI Translation", st.session_state['translated_text'], height=300)
                
                with col2:
                    st.subheader("Reference Quebec French")
                    st.text_area("Reference Translation", reference_text, height=300)
                
                # Calculate accuracy metrics
                accuracy_results = calculate_keyword_accuracy(
                    st.session_state['translated_text'],
                    reference_text
                )
                
                # Display accuracy metrics
                st.subheader("Translation Accuracy Analysis")
                
                # Accuracy score
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Keyword Overlap", f"{accuracy_results['overlap_percentage']}%")
                with col2:
                    st.metric("Common Words", accuracy_results['common_words'])
                with col3:
                    st.metric("Reference Words", accuracy_results['reference_words'])
                
                # Important keywords found in both
                st.subheader("Important Matching Keywords")
                if accuracy_results['important_keywords']:
                    keyword_cols = st.columns(4)
                    keywords_per_col = len(accuracy_results['important_keywords']) // 4 + 1
                    
                    for i, col in enumerate(keyword_cols):
                        start_idx = i * keywords_per_col
                        end_idx = min((i + 1) * keywords_per_col, len(accuracy_results['important_keywords']))
                        col_keywords = accuracy_results['important_keywords'][start_idx:end_idx]
                        
                        for keyword in col_keywords:
                            col.markdown(f"• {keyword}")
                else:
                    st.write("No significant matching keywords found")
                
                # Provide assessment
                st.subheader("Translation Assessment")
                if accuracy_results['overlap_percentage'] >= 70:
                    st.success("The AI translation shows strong alignment with the reference Quebec French document.")
                elif accuracy_results['overlap_percentage'] >= 50:
                    st.info("The AI translation shows moderate alignment with the reference Quebec French document.")
                else:
                    st.warning("The AI translation shows significant differences from the reference Quebec French document.")

if __name__ == "__main__":
    main()

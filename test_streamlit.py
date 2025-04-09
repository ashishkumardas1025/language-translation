# app.py
import streamlit as st
import mammoth
import os
import docx
import tempfile
import base64
from io import BytesIO
from quebec_translation import process_document_for_quebec_french, calculate_cosine_similarity

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
    
    # Calculate cosine similarity
    cosine_sim = calculate_cosine_similarity(generated_text, reference_text) * 100
        
    return {
        "overlap_percentage": round(overlap_percentage, 2),
        "cosine_similarity": round(cosine_sim, 2),
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
        
        st.markdown("### Custom Banking Terminology")
        
        # Default banking terms
        default_banking_terms = """{
    "help": "aide",
    "sign out": "quitter",
    "account": "compte",
    "balance": "solde",
    "transfer": "virement",
    "deposit": "dépôt",
    "withdrawal": "retrait",
    "credit card": "carte de crédit",
    "debit card": "carte de débit"
}"""
        
        custom_terms_json = st.text_area(
            "Custom Banking Terms (JSON format)",
            value=default_banking_terms,
            height=200
        )
        
        try:
            custom_terms = json.loads(custom_terms_json)
        except:
            st.error("Invalid JSON format. Please check your custom terms.")
            custom_terms = {}
        
        st.divider()
        
        st.markdown("### About")
        st.markdown("""
        This app uses AI to translate documents to authentic Quebec French while preserving:
        - Original formatting and document structure
        - Quebec French terminology and expressions
        - Technical banking terminology with Quebec French equivalents
        """)
    
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
            
            # Start translation button
            if st.button("Translate to Quebec French"):
                with st.spinner("Translating document to Quebec French..."):
                    # Progress tracking
                    progress_bar = st.progress(0)
                    
                    # Step 1: Translation preparation
                    st.markdown("🔍 Preparing for translation...")
                    progress_bar.progress(25)
                    
                    # Step 2: Translation
                    st.markdown("📝 Translating to Quebec French...")
                    progress_bar.progress(50)
                    
                    # Step 3: Quebec authenticity check
                    st.markdown("⚜️ Verifying Quebec French authenticity...")
                    progress_bar.progress(75)
                    
                    # Run the full translation process
                    result = process_document_for_quebec_french(text_content, custom_terms)
                    
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
                        
                        # Translation quality metrics
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            with st.expander("Banking Terminology Usage"):
                                if "quality_review" in result and result["quality_review"]:
                                    if "custom_terminology_compliance" in result["quality_review"]:
                                        st.write(result["quality_review"]["custom_terminology_compliance"])
                                    else:
                                        st.write("Custom banking terminology was applied to the translation.")
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
                        
                        # Display quality review if available
                        if "quality_review" in result and result["quality_review"]:
                            with st.expander("Translation Quality Assessment"):
                                st.json(result["quality_review"])
                        
                        # Quebec French language tips
                        st.markdown("""
                        ### 💡 Quebec French Language Tips
                        
                        This translation uses authentic Quebec French expressions and banking terminology. Some key differences from International French include:
                        
                        - Different vocabulary choices unique to Quebec
                        - Contractions and speech patterns common in Quebec
                        - Banking terminology using Quebec industry standards
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
                    st.metric("Cosine Similarity", f"{accuracy_results['cosine_similarity']}%")
                with col3:
                    st.metric("Common Words", accuracy_results['common_words'])
                
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
                cos_sim = accuracy_results['cosine_similarity']
                if cos_sim >= 80:
                    st.success(f"The AI translation shows excellent alignment with the reference Quebec French document (Cosine similarity: {cos_sim}%).")
                elif cos_sim >= 60:
                    st.info(f"The AI translation shows good alignment with the reference Quebec French document (Cosine similarity: {cos_sim}%).")
                else:
                    st.warning(f"The AI translation shows significant differences from the reference Quebec French document (Cosine similarity: {cos_sim}%).")

if __name__ == "__main__":
    main()





#######################################
# Add this import at the top of app.py
from quebec_translation import process_document_for_quebec_french, calculate_cosine_similarity, assess_semantic_accuracy

# Then replace the validation tab code in your main() function with this updated version:

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
            
            # Start the accuracy assessment
            with st.spinner("Analyzing translation accuracy..."):
                # Calculate statistical accuracy metrics
                statistical_accuracy = calculate_keyword_accuracy(
                    st.session_state['translated_text'],
                    reference_text
                )
                
                # Custom terms from session state if available
                try:
                    custom_terms = json.loads(custom_terms_json)
                except:
                    custom_terms = {}
                
                # Run semantic accuracy assessment with Claude
                with st.status("Performing semantic analysis...", expanded=True) as status:
                    st.write("Analyzing meaning preservation...")
                    st.write("Evaluating Quebec French authenticity...")
                    st.write("Comparing terminology usage...")
                    
                    semantic_assessment = assess_semantic_accuracy(
                        st.session_state['translated_text'],
                        reference_text,
                        custom_terms
                    )
                    
                    status.update(label="Semantic analysis complete!", state="complete")
            
            # Display metrics in tabs
            accuracy_tabs = st.tabs(["Semantic Analysis", "Statistical Metrics", "Term Usage"])
            
            # Tab 1: Semantic analysis results
            with accuracy_tabs[0]:
                if "error" in semantic_assessment:
                    st.error(f"Error in semantic assessment: {semantic_assessment['error']}")
                else:
                    # Display semantic scores with gauges
                    st.subheader("Semantic Understanding Metrics")
                    sem_cols = st.columns(4)
                    
                    semantic_score = semantic_assessment.get("semantic_accuracy_score", 0)
                    if isinstance(semantic_score, str): 
                        semantic_score = float(semantic_score)
                        
                    quebec_score = semantic_assessment.get("quebec_french_authenticity_comparison", 0)
                    if isinstance(quebec_score, str):
                        quebec_score = float(quebec_score)
                        
                    fluency_score = semantic_assessment.get("fluency_comparison", 0)
                    if isinstance(fluency_score, str):
                        fluency_score = float(fluency_score)
                        
                    terminology_score = semantic_assessment.get("terminology_consistency_score", 0)
                    if isinstance(terminology_score, str):
                        terminology_score = float(terminology_score)
                    
                    with sem_cols[0]:
                        st.metric("Semantic Accuracy", f"{semantic_score}/10")
                    with sem_cols[1]:
                        st.metric("Quebec Authenticity", f"{quebec_score}/10")
                    with sem_cols[2]:
                        st.metric("Fluency", f"{fluency_score}/10")
                    with sem_cols[3]:
                        st.metric("Terminology", f"{terminology_score}/10")
                    
                    # Overall assessment
                    st.subheader("Overall Assessment")
                    overall = semantic_assessment.get("overall_assessment", "No assessment available")
                    
                    # Color background based on average score
                    avg_score = (semantic_score + quebec_score + fluency_score + terminology_score) / 4
                    if avg_score >= 8:
                        st.success(overall)
                    elif avg_score >= 6:
                        st.info(overall)
                    else:
                        st.warning(overall)
                    
                    # Detailed findings
                    st.subheader("Detailed Findings")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Key Differences")
                        key_differences = semantic_assessment.get("key_differences", "No key differences identified")
                        if isinstance(key_differences, list):
                            for diff in key_differences:
                                st.markdown(f"• {diff}")
                        else:
                            st.write(key_differences)
                        
                        st.markdown("#### Missing Quebec Expressions")
                        missing_expressions = semantic_assessment.get("missing_quebec_expressions", "No missing expressions identified")
                        if isinstance(missing_expressions, list):
                            for expr in missing_expressions:
                                st.markdown(f"• {expr}")
                        else:
                            st.write(missing_expressions)
                    
                    with col2:
                        st.markdown("#### Translation Strengths")
                        strengths = semantic_assessment.get("strengths", "No specific strengths identified")
                        if isinstance(strengths, list):
                            for strength in strengths:
                                st.markdown(f"• {strength}")
                        else:
                            st.write(strengths)
            
            # Tab 2: Statistical metrics
            with accuracy_tabs[1]:
                st.subheader("Statistical Accuracy Metrics")
                
                # Accuracy score
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Keyword Overlap", f"{statistical_accuracy['overlap_percentage']}%")
                with col2:
                    st.metric("Cosine Similarity", f"{statistical_accuracy['cosine_similarity']}%")
                with col3:
                    st.metric("Common Words", statistical_accuracy['common_words'])
                
                # Important keywords found in both
                st.subheader("Important Matching Keywords")
                if statistical_accuracy['important_keywords']:
                    keyword_cols = st.columns(4)
                    keywords_per_col = len(statistical_accuracy['important_keywords']) // 4 + 1
                    
                    for i, col in enumerate(keyword_cols):
                        start_idx = i * keywords_per_col
                        end_idx = min((i + 1) * keywords_per_col, len(statistical_accuracy['important_keywords']))
                        col_keywords = statistical_accuracy['important_keywords'][start_idx:end_idx]
                        
                        for keyword in col_keywords:
                            col.markdown(f"• {keyword}")
                else:
                    st.write("No significant matching keywords found")
            
            # Tab 3: Term usage visualization
            with accuracy_tabs[2]:
                st.subheader("Banking Terminology Comparison")
                
                # Check if custom terms were provided
                if custom_terms:
                    # Create a dataframe to visualize term usage
                    term_data = []
                    
                    for english_term, french_term in custom_terms.items():
                        # Check if translated text contains the term
                        ai_contains = french_term.lower() in st.session_state['translated_text'].lower()
                        ref_contains = french_term.lower() in reference_text.lower()
                        
                        term_data.append({
                            "English Term": english_term,
                            "Quebec French Term": french_term,
                            "In AI Translation": "✅" if ai_contains else "❌",
                            "In Reference": "✅" if ref_contains else "❌",
                            "Match": "✅" if ai_contains == ref_contains else "❌"
                        })
                    
                    if term_data:
                        import pandas as pd
                        term_df = pd.DataFrame(term_data)
                        st.dataframe(term_df, use_container_width=True)
                        
                        # Calculate match percentage
                        matches = sum(1 for item in term_data if item["Match"] == "✅")
                        match_percentage = (matches / len(term_data)) * 100 if term_data else 0
                        
                        st.metric("Banking Term Match Rate", f"{round(match_percentage, 1)}%")
                    else:
                        st.info("No custom banking terms were provided for analysis.")
                else:
                    st.info("No custom banking terms were provided for comparison.")
            
            # Add a comparison summary
            st.subheader("Translation Quality Summary")
            
            # Combine statistical and semantic metrics for an overall score
            avg_semantic = (semantic_score + quebec_score + fluency_score + terminology_score) / 4 if "error" not in semantic_assessment else 0
            stat_score = statistical_accuracy['cosine_similarity'] / 10  # Convert to same 0-10 scale
            
            # Weight semantic more heavily (70%) than statistical (30%)
            weighted_score = (avg_semantic * 0.7) + (stat_score * 0.3)
            
            # Display overall quality assessment
            if weighted_score >= 8:
                st.success(f"The AI translation shows excellent alignment with the reference Quebec French document (Overall score: {weighted_score:.1f}/10).")
            elif weighted_score >= 6:
                st.info(f"The AI translation shows good alignment with the reference Quebec French document (Overall score: {weighted_score:.1f}/10).")
            else:
                st.warning(f"The AI translation shows significant differences from the reference Quebec French document (Overall score: {weighted_score:.1f}/10).")

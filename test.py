ef assess_semantic_accuracy(
    generated_text: str,
    reference_text: str,
    custom_terms: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Use Claude to assess semantic accuracy between generated and reference translations
    by comparing meaning preservation, tone, and Quebec French authenticity.
    Simplified version without detailed analysis.
    """
    if not generated_text or not reference_text:
        return {"error": "Missing generated or reference text"}
    
    system_prompt = """You are an expert Quebec French linguistic evaluator with deep knowledge of Quebec language, 
    culture, and linguistic nuances. Your task is to compare a machine-generated Quebec French translation with a 
    reference human translation, providing a focused numerical assessment of key metrics."""
    
    # For long texts, check a sample of the beginning, middle and end
    if len(generated_text) > 3000 or len(reference_text) > 3000:
        # Get samples from beginning, middle and end
        gen_samples = [
            generated_text[:800],
            generated_text[len(generated_text)//2-400:len(generated_text)//2+400],
            generated_text[-800:]
        ]
        
        ref_samples = [
            reference_text[:800],
            reference_text[len(reference_text)//2-400:len(reference_text)//2+400],
            reference_text[-800:]
        ]
        
        assessment_prompt = f"""Compare the following machine-generated Quebec French translation with the reference human translation.

MACHINE-GENERATED TRANSLATION (SAMPLES):
Beginning: {gen_samples[0]}

Middle: {gen_samples[1]}

End: {gen_samples[2]}

REFERENCE HUMAN TRANSLATION (SAMPLES):
Beginning: {ref_samples[0]}

Middle: {ref_samples[1]}

End: {ref_samples[2]}

Please evaluate the semantic accuracy of the machine-generated translation compared to the reference. Provide only:

1. Semantic Accuracy Score (1-10): How well the generated translation preserves the meaning of the reference translation
2. Quebec French Authenticity Comparison (1-10): How the generated translation compares to the reference in terms of authentic Quebec French expressions and terminology
3. Fluency Comparison (1-10): How natural the generated translation sounds compared to the reference
4. Terminology Consistency Score (1-10): How consistently domain terminology is used compared to the reference

Respond in JSON format with just these 4 scores.
"""
    else:
        assessment_prompt = f"""Compare the following machine-generated Quebec French translation with the reference human translation.

MACHINE-GENERATED TRANSLATION:
{generated_text}

REFERENCE HUMAN TRANSLATION:
{reference_text}

Please evaluate the semantic accuracy of the machine-generated translation compared to the reference. Provide only:

1. Semantic Accuracy Score (1-10): How well the generated translation preserves the meaning of the reference translation
2. Quebec French Authenticity Comparison (1-10): How the generated translation compares to the reference in terms of authentic Quebec French expressions and terminology
3. Fluency Comparison (1-10): How natural the generated translation sounds compared to the reference
4. Terminology Consistency Score (1-10): How consistently domain terminology is used compared to the reference

Respond in JSON format with just these 4 scores.
"""
    
    assessment_result = invoke_bedrock_claude(assessment_prompt, system_prompt, max_tokens=1000)
    assessment_data = extract_json(assessment_result)
    
    return assessment_data
####################################################3
def translate_document_to_quebec_french(
    text_content: str,
    custom_terms: Dict[str, str] = None
) -> Dict[str, Any]:
    """Translate document content to Quebec French while preserving formatting and style"""
    if not text_content:
        return {"error": "No text content provided"}
    
    # Build system prompt
    system_prompt = """You are an expert Quebec French translator. You are translating for a Quebec audience 
    and must use Quebec French vocabulary, expressions, and grammar patterns. Translate accurately while preserving 
    the original formatting, tone, and style.
    
    Important Quebec French translation guidelines:
    1. Use Quebec French terminology and expressions rather than International French
    2. Apply Quebec grammar conventions
    3. Use Quebec idioms when appropriate for the context
    4. Preserve the original formatting, paragraph structure, and style"""
    
    # Format custom terminology if provided
    custom_terms_str = ""
    if custom_terms:
        custom_terms_str = "\nTerminology to use (always use these specific translations):\n" + json.dumps(custom_terms, indent=2)
    
    translation_prompt = f"""Please translate the following text from English to Quebec French (Canadian French). 
This translation is specifically intended for a Quebec audience, not a general French-speaking audience.

{custom_terms_str}

TEXT TO TRANSLATE:
{text_content}

Translation (in Quebec French):"""
    
    translation = invoke_bedrock_claude(
        prompt=translation_prompt,
        system=system_prompt,
        max_tokens=min(100000, len(text_content) * 2)  # Adjust max tokens based on input length
    )
    
    return {
        "original_text": text_content,
        "translated_text": translation,
        "target_language": "Quebec French"
    }

def check_quebec_french_quality(
    original_text: str, 
    translated_text: str,
    custom_terms: Dict[str, str] = None
) -> Dict[str, Any]:
    """Verify Quebec French translation quality"""
    if not original_text or not translated_text:
        return {"error": "Missing original or translated text"}
    
    system_prompt = """You are an expert Quebec French reviewer with deep knowledge of Quebec language and culture. 
    Your task is to review translations for accuracy, fluency, and whether they properly reflect Quebec French 
    rather than International French."""
    
    # For long texts, check a sample
    if len(original_text) > 3000:
        # Get samples from beginning, middle and end
        orig_samples = [
            original_text[:1000],
            original_text[len(original_text)//2-500:len(original_text)//2+500],
            original_text[-1000:]
        ]
        
        trans_samples = [
            translated_text[:1000],
            translated_text[len(translated_text)//2-500:len(translated_text)//2+500],
            translated_text[-1000:]
        ]
        
        review_prompt = f"""Review the quality of this translation from English to Quebec French.

ORIGINAL TEXT (SAMPLES):
Beginning: {orig_samples[0]}

Middle: {orig_samples[1]}

End: {orig_samples[2]}

TRANSLATION (CORRESPONDING SECTIONS):
Beginning: {trans_samples[0]}

Middle: {trans_samples[1]}

End: {trans_samples[2]}

Please provide only:
1. Overall quality assessment (1-10)
2. Quebec French authenticity (1-10, where 10 means perfectly Quebec French)
3. Accuracy assessment (1-10)
4. Fluency assessment (1-10)

Respond in JSON format.
"""
    else:
        review_prompt = f"""Review the quality of this translation from English to Quebec French.

ORIGINAL TEXT:
{original_text}

TRANSLATION:
{translated_text}

Please provide only:
1. Overall quality assessment (1-10)
2. Quebec French authenticity (1-10, where 10 means perfectly Quebec French)
3. Accuracy assessment (1-10)
4. Fluency assessment (1-10)

Respond in JSON format.
"""
    
    review_result = invoke_bedrock_claude(review_prompt, system_prompt, max_tokens=1000)
    review_data = extract_json(review_result)
    
    return {
        "translated_text": translated_text,
        "quality_review": review_data
    }

def process_document_for_quebec_french(
    text_content: str,
    custom_terms: Dict[str, str] = None
) -> Dict[str, Any]:
    """Run the complete Quebec French translation workflow"""
    
    # Step 1: Quebec French translation
    translation_result = translate_document_to_quebec_french(
        text_content, 
        custom_terms
    )
    
    if "error" in translation_result:
        return {"error": translation_result["error"], "stage": "translation"}
    
    # Step 2: Quebec French quality check
    quality_result = check_quebec_french_quality(
        text_content,
        translation_result.get("translated_text", ""),
        custom_terms
    )
    
    if "error" in quality_result:
        return {"error": quality_result["error"], "stage": "quality_check"}
    
    # Return the final result
    return {
        "original_text": text_content,
        "translated_text": quality_result.get("translated_text", ""),
        "quality_review": quality_result.get("quality_review", {}),
        "target_language": "Quebec French"
    }

##################################################3
# app.py
import streamlit as st
import mammoth
import os
import docx
import tempfile
import base64
from io import BytesIO
from quebec_translation import process_document_for_quebec_french, calculate_cosine_similarity, assess_semantic_accuracy
import json

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
    
    # Default banking terms - now hardcoded instead of in UI
    default_banking_terms = {
        "help": "aide",
        "sign out": "quitter",
        "account": "compte",
        "balance": "solde",
        "transfer": "virement",
        "deposit": "dépôt",
        "withdrawal": "retrait",
        "credit card": "carte de crédit",
        "debit card": "carte de débit"
    }
    
    with st.sidebar:
        st.header("About")
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
                    
                    # Run the full translation process with hardcoded banking terms
                    result = process_document_for_quebec_french(text_content, default_banking_terms)
                    
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
                        
                        # Simplified translation quality metrics
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
                    
                    # Run semantic accuracy assessment with Claude
                    with st.status("Performing semantic analysis...", expanded=True) as status:
                        st.write("Analyzing meaning preservation...")
                        st.write("Evaluating Quebec French authenticity...")
                        
                        semantic_assessment = assess_semantic_accuracy(
                            st.session_state['translated_text'],
                            reference_text,
                            default_banking_terms
                        )
                        
                        status.update(label="Semantic analysis complete!", state="complete")
                
                # Display accuracy metrics in tabs
                accuracy_tabs = st.tabs(["Semantic Analysis", "Statistical Metrics"])
                
                # Tab 1: Semantic analysis results - simplified
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
                
                # Tab 2: Statistical metrics - simplified
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

if __name__ == "__main__":
    main()

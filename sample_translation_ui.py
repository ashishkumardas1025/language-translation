import streamlit as st
import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import word_tokenize
from translation_code import translate_to_canadian_french, translate_file

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

def calculate_metrics(original_text, translated_text, reference_text=None):
    """Calculate various metrics between translated text and reference (if available)."""
    metrics = {}
    
    # If no reference is available, we can't calculate comparison metrics
    if reference_text is None:
        return {
            "word_count_original": len(word_tokenize(original_text)),
            "word_count_translated": len(word_tokenize(translated_text)),
            "length_ratio": len(translated_text) / max(len(original_text), 1) if original_text else 0
        }
    
    # Tokenize texts
    original_tokens = word_tokenize(original_text.lower())
    translated_tokens = word_tokenize(translated_text.lower()) if translated_text else []
    reference_tokens = word_tokenize(reference_text.lower()) if reference_text else []
    
    # Word counts
    metrics["word_count_original"] = len(original_tokens)
    metrics["word_count_translated"] = len(translated_tokens)
    metrics["word_count_reference"] = len(reference_tokens)
    
    # Length ratio (translated / original)
    metrics["length_ratio"] = len(translated_text) / max(len(original_text), 1) if original_text else 0
    
    # Common overlap words count
    common_words = set(translated_tokens).intersection(set(reference_tokens))
    metrics["common_word_count"] = len(common_words)
    metrics["common_words"] = ", ".join(list(common_words)[:20]) + ("..." if len(common_words) > 20 else "")
    
    # Word overlap percentage
    if reference_tokens:
        metrics["overlap_percentage"] = round((len(common_words) / len(set(reference_tokens))) * 100, 2)
    else:
        metrics["overlap_percentage"] = 0
    
    # Cosine similarity
    try:
        vectorizer = CountVectorizer().fit_transform([translated_text, reference_text])
        vectors = vectorizer.toarray()
        metrics["cosine_similarity"] = round(cosine_similarity(vectors)[0][1] * 100, 2)
    except:
        metrics["cosine_similarity"] = 0
    
    return metrics

def main():
    st.set_page_config(page_title="Canadian French Translator & Validator", layout="wide")
    
    st.title("🍁 Canadian French Translation Tool")
    st.write("Translate text to Canadian French with quality metrics")
    
    # Check if AWS credentials are set
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not aws_key or not aws_secret:
        st.error("⚠️ AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        st.stop()
    
    tab1, tab2 = st.tabs(["Text Translation", "File Translation & Metrics"])
    
    # Text Translation Tab
    with tab1:
        st.header("Text Translation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Original Text")
            user_text = st.text_area(
                "Enter text to translate",
                height=300,
                placeholder="Enter English text here..."
            )
            
            if st.button("Translate", key="translate_text_btn"):
                if user_text:
                    with st.spinner("Translating..."):
                        translated = translate_to_canadian_french(user_text)
                        if translated:
                            st.session_state.translated_text = translated
                        else:
                            st.error("Translation failed. Please try again.")
                else:
                    st.warning("Please enter some text to translate.")
        
        with col2:
            st.subheader("Canadian French Translation")
            if 'translated_text' in st.session_state:
                st.text_area(
                    "Translation result",
                    value=st.session_state.translated_text,
                    height=300,
                    key="result_text_area"
                )
            else:
                st.text_area(
                    "Translation result",
                    value="",
                    height=300,
                    disabled=True,
                    placeholder="Translation will appear here..."
                )
    
    # File Translation & Metrics Tab
    with tab2:
        st.header("File Translation with Metrics")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader("Upload a text file (.txt, .md, .csv, .json)", type=["txt", "md", "csv", "json"])
            
            if uploaded_file is not None:
                # Save the uploaded file temporarily
                temp_file_path = f"temp_{uploaded_file.name}"
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                st.success(f"File uploaded: {uploaded_file.name}")
        
        with col2:
            reference_file = st.file_uploader("Upload reference translation (optional)", type=["txt", "md", "csv", "json"])
            
            reference_path = None
            if reference_file is not None:
                reference_path = f"ref_{reference_file.name}"
                with open(reference_path, "wb") as f:
                    f.write(reference_file.getvalue())
                
                st.success(f"Reference file uploaded: {reference_file.name}")
        
        if uploaded_file is not None:
            if st.button("Translate File and Calculate Metrics"):
                with st.spinner("Translating file content..."):
                    output_path = translate_file(temp_file_path)
                    
                    if output_path:
                        # Read all file contents
                        with open(temp_file_path, "r", encoding="utf-8") as f:
                            original_content = f.read()
                        
                        with open(output_path, "r", encoding="utf-8") as f:
                            translated_content = f.read()
                        
                        reference_content = None
                        if reference_path:
                            try:
                                with open(reference_path, "r", encoding="utf-8") as f:
                                    reference_content = f.read()
                            except:
                                st.warning("Could not read reference file. Metrics will be limited.")
                        
                        # Display original and translated content
                        st.success(f"Translation complete! Saved to {output_path}")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Original Content")
                            st.text_area("", value=original_content, height=300, key="orig_file_content")
                        
                        with col2:
                            st.subheader("Translated Content")
                            st.text_area("", value=translated_content, height=300, key="trans_file_content")
                        
                        # Calculate metrics
                        metrics = calculate_metrics(original_content, translated_content, reference_content)
                        
                        # Display metrics
                        st.subheader("Translation Metrics")
                        
                        # Basic metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Original Word Count", metrics["word_count_original"])
                        with col2:
                            st.metric("Translated Word Count", metrics["word_count_translated"])
                        with col3:
                            st.metric("Length Ratio", f"{metrics['length_ratio']:.2f}")
                        
                        # Reference comparison metrics (if reference is available)
                        if reference_content:
                            st.write("---")
                            st.subheader("Reference Comparison Metrics")
                            
                            # Display reference text
                            st.text_area("Reference Translation", value=reference_content, height=200)
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Common Word Count", metrics["common_word_count"])
                            with col2:
                                st.metric("Word Overlap %", f"{metrics['overlap_percentage']}%")
                            with col3:
                                st.metric("Cosine Similarity", f"{metrics['cosine_similarity']}%")
                            
                            st.write("**Common words found:**")
                            st.write(metrics["common_words"])
                            
                            # Create comparison DataFrame
                            if metrics["word_count_reference"] > 0:
                                data = {
                                    "Metric": ["Word Count", "Overlap %", "Cosine Similarity"],
                                    "Value": [
                                        f"{metrics['word_count_translated']} / {metrics['word_count_reference']}",
                                        f"{metrics['overlap_percentage']}%",
                                        f"{metrics['cosine_similarity']}%"
                                    ]
                                }
                                st.dataframe(pd.DataFrame(data))
                        
                        # Offer download of translated file
                        with open(output_path, "rb") as file:
                            st.download_button(
                                label="Download translated file",
                                data=file,
                                file_name=os.path.basename(output_path),
                                mime="text/plain"
                            )
                        
                        # Export metrics as CSV
                        metrics_df = pd.DataFrame({k: [v] for k, v in metrics.items() if not isinstance(v, str)})
                        csv = metrics_df.to_csv(index=False)
                        st.download_button(
                            label="Download metrics as CSV",
                            data=csv,
                            file_name="translation_metrics.csv",
                            mime="text/csv",
                            key="download-metrics"
                        )
                    else:
                        st.error("Translation failed. Please check the logs.")

if __name__ == "__main__":
    main()

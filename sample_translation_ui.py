import streamlit as st
import os
import pandas as pd
from translation_code import translate_to_canadian_french, translate_file

def main():
    st.set_page_config(page_title="Canadian French Translator & Validator", layout="wide")
    
    st.title("🍁 Canadian French Translation Tool")
    st.write("Translate text to Canadian French and validate against reference translations")
    
    # Check if AWS credentials are set
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not aws_key or not aws_secret:
        st.error("⚠️ AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["Text Translation", "File Translation", "Batch Validation"])
    
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
    
    # File Translation Tab
    with tab2:
        st.header("File Translation")
        
        uploaded_file = st.file_uploader("Upload a text file (.txt, .md, .csv, .json)", type=["txt", "md", "csv", "json"])
        
        if uploaded_file is not None:
            # Save the uploaded file temporarily
            temp_file_path = f"temp_{uploaded_file.name}"
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            st.success(f"File uploaded: {uploaded_file.name}")
            
            if st.button("Translate File"):
                with st.spinner("Translating file content..."):
                    output_path = translate_file(temp_file_path)
                    
                    if output_path:
                        with open(output_path, "r", encoding="utf-8") as f:
                            translated_content = f.read()
                        
                        st.success(f"Translation complete! Saved to {output_path}")
                        
                        # Display original and translated content
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Original Content")
                            with open(temp_file_path, "r", encoding="utf-8") as f:
                                original_content = f.read()
                            st.text_area("", value=original_content, height=400, key="orig_file_content")
                        
                        with col2:
                            st.subheader("Translated Content")
                            st.text_area("", value=translated_content, height=400, key="trans_file_content")
                        
                        # Offer download of translated file
                        with open(output_path, "rb") as file:
                            st.download_button(
                                label="Download translated file",
                                data=file,
                                file_name=os.path.basename(output_path),
                                mime="text/plain"
                            )
                    else:
                        st.error("Translation failed. Please check the logs.")
    
    # Batch Validation Tab
    with tab3:
        st.header("Translation Validation")
        st.write("Upload a CSV file with original texts and their reference Canadian French translations to validate against the model's translations.")
        
        st.markdown("""
        **CSV Format Required:**
        - Column 1: `original` - Original English text
        - Column 2: `reference` - Reference Canadian French translation
        """)
        
        validation_file = st.file_uploader("Upload validation CSV", type=["csv"])
        
        if validation_file is not None:
            try:
                df = pd.read_csv(validation_file)
                
                if 'original' not in df.columns or 'reference' not in df.columns:
                    st.error("CSV must contain 'original' and 'reference' columns")
                else:
                    st.write(f"Loaded {len(df)} validation pairs")
                    
                    if st.button("Run Validation"):
                        results = []
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, row in enumerate(df.itertuples()):
                            status_text.text(f"Translating item {i+1}/{len(df)}...")
                            
                            model_translation = translate_to_canadian_french(row.original)
                            
                            # Simple string matching score (0-100)
                            match_score = 0
                            if model_translation and row.reference:
                                # Count matching words
                                model_words = set(model_translation.lower().split())
                                ref_words = set(row.reference.lower().split())
                                
                                if len(ref_words) > 0:
                                    intersection = model_words.intersection(ref_words)
                                    match_score = round((len(intersection) / len(ref_words)) * 100)
                            
                            results.append({
                                "original": row.original,
                                "reference": row.reference,
                                "model_translation": model_translation,
                                "match_score": match_score
                            })
                            
                            progress_bar.progress((i + 1) / len(df))
                        
                        results_df = pd.DataFrame(results)
                        average_score = results_df['match_score'].mean()
                        
                        st.success(f"Validation complete! Average match score: {average_score:.2f}%")
                        
                        st.subheader("Validation Results")
                        st.dataframe(
                            results_df[['original', 'reference', 'model_translation', 'match_score']], 
                            use_container_width=True
                        )
                        
                        # Create downloadable results
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            "Download validation results",
                            csv,
                            "validation_results.csv",
                            "text/csv",
                            key='download-csv'
                        )
            except Exception as e:
                st.error(f"Error processing validation file: {e}")

if __name__ == "__main__":
    main()

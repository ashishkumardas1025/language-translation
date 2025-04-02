import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
import mammoth
import os
import uuid
import docx
import json
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any

app = FastAPI()

# Add CORS middleware to allow requests from Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize AWS Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'  # Change to your preferred AWS region
)

# Create storage directory
os.makedirs("temp", exist_ok=True)

class TranslationRequest(BaseModel):
    file_id: str
    target_language: str = "French"
    quality_level: str = "Standard"
    preserve_formatting: bool = True
    include_analysis: bool = True

class ChatRequest(BaseModel):
    file_id: str
    query: str
    history: List[Dict[str, str]] = []

def call_claude(prompt, system="", max_tokens=4000, temperature=0.3):
    """Call Claude 3.5 Sonnet via AWS Bedrock"""
    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        if system:
            request_body["system"] = system
            
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',  # Claude 3.5 Sonnet model ID
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read().decode('utf-8'))
        return response_body['content'][0]['text']
    except Exception as e:
        print(f"Error calling Claude: {str(e)}")
        return f"Error: {str(e)}"

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document and extract its text content"""
    
    file_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1].lower()
    
    # Create temp directory if it doesn't exist
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/{file_id}.{file_extension}"
    
    # Save the file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Extract text based on file type
    text_content = ""
    try:
        if file_extension == "docx":
            # Handle Word documents - correct usage of mammoth
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
                text_content = result.value
        elif file_extension == "txt":
            # Handle plain text
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    return {"file_id": file_id, "filename": file.filename, "text_content": text_content}

@app.get("/api/documents")
async def get_documents():
    """Get a list of all available documents"""
    documents = []
    
    try:
        files = os.listdir("temp")
        
        # Group files by their ID (base file and translated file)
        file_groups = {}
        
        for file in files:
            # Skip temporary files
            if file.startswith('.') or file.endswith('.tmp'):
                continue
                
            file_parts = file.split('.')
            if len(file_parts) < 2:
                continue
                
            # Handle translated files
            if "_translated" in file:
                file_id = file.split('_translated')[0]
            else:
                file_id = file_parts[0]
                
            if file_id not in file_groups:
                file_groups[file_id] = {"original": None, "translated": None}
                
            if "_translated" in file:
                file_groups[file_id]["translated"] = file
            else:
                file_groups[file_id]["original"] = file
        
        # Create document entries
        for file_id, files in file_groups.items():
            if files["original"]:
                original_path = f"temp/{files['original']}"
                file_extension = files["original"].split('.')[-1]
                
                # Extract filename from the path
                original_filename = files["original"].split('.')
                if len(original_filename) > 1:
                    original_filename = original_filename[1] + "." + file_extension
                else:
                    original_filename = f"document.{file_extension}"
                
                # Get basic file info
                file_size = os.path.getsize(original_path)
                
                # Create document entry
                doc_entry = {
                    "file_id": file_id,
                    "filename": original_filename,
                    "file_type": file_extension,
                    "file_size": file_size,
                    "has_translation": files["translated"] is not None
                }
                
                documents.append(doc_entry)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")
    
    return documents

@app.post("/api/translate")
async def translate_document(translation_request: TranslationRequest):
    """Translate document content using Claude"""
    
    file_id = translation_request.file_id
    target_language = translation_request.target_language
    quality_level = translation_request.quality_level
    
    # Find the file
    files = os.listdir("temp")
    file_path = None
    for f in files:
        if f.startswith(file_id) and "_translated" not in f:
            file_path = f"temp/{f}"
            break
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Extract text
    file_extension = file_path.split('.')[-1].lower()
    text_content = ""
    
    try:
        if file_extension == "docx":
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
                text_content = result.value
        elif file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
    
    # Set temperature based on quality level
    temp_settings = {
        "Draft": 0.5,
        "Standard": 0.3,
        "High": 0.2,
        "Professional": 0.1
    }
    temperature = temp_settings.get(quality_level, 0.3)
    
    # Use Claude to translate
    prompt = f"""Please translate the following text from English to {target_language}. 
Maintain the original formatting, paragraphs, and style as much as possible:

{text_content}

Translation:"""
    
    system = "You are an expert translator specialized in preserving document formatting while translating accurately."
    
    try:
        translation = call_claude(
            prompt=prompt,
            system=system,
            max_tokens=100000,
            temperature=temperature
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")
    
    # Generate document analysis
    analysis_prompt = f"""Analyze the following document text and provide structured information about it:

{text_content}

Please provide a JSON response with the following structure:
{{
  "document_type": "Article/Email/Contract/etc",
  "primary_language": "The detected primary language",
  "word_count": Number of words,
  "complexity_level": "Basic/Intermediate/Advanced",
  "key_topics": ["Topic1", "Topic2", "Topic3"],
  "tone": "Formal/Informal/Technical/etc",
  "readability_metrics": {{
    "average_sentence_length": Number of words,
    "complex_word_percentage": Percentage as number
  }}
}}"""

    # Generate quality review
    quality_prompt = f"""Review the quality of the following translation from English to {target_language}:

Original:
{text_content}

Translation:
{translation}

Please provide a JSON response with the following structure:
{{
  "quality_score": Score from 1-10,
  "metrics": {{
    "accuracy": Score from 1-10,
    "fluency": Score from 1-10,
    "terminology": Score from 1-10,
    "style": Score from 1-10
  }},
  "notes": [
    "Note about strength or weakness 1",
    "Note about strength or weakness 2"
  ]
}}"""

    document_analysis = {}
    quality_review = {}
    
    if translation_request.include_analysis:
        try:
            analysis_result = call_claude(
                prompt=analysis_prompt,
                system="You are a document analysis expert. Provide only the JSON response.",
                max_tokens=2000,
                temperature=0.1
            )
            
            # Extract JSON from Claude's response
            analysis_json = extract_json(analysis_result)
            if analysis_json:
                document_analysis = analysis_json
                
            quality_result = call_claude(
                prompt=quality_prompt,
                system="You are a translation quality assessment expert. Provide only the JSON response.",
                max_tokens=2000,
                temperature=0.1
            )
            
            # Extract JSON from Claude's response
            quality_json = extract_json(quality_result)
            if quality_json:
                quality_review = quality_json
                
        except Exception as e:
            print(f"Analysis error (non-critical): {str(e)}")
    
    # Save translation
    translated_file_path = f"temp/{file_id}_translated.{file_extension}"
    
    try:
        if file_extension == "docx":
            doc = docx.Document()
            for paragraph in translation.split('\n'):
                doc.add_paragraph(paragraph)
            doc.save(translated_file_path)
        elif file_extension == "txt":
            with open(translated_file_path, "w", encoding="utf-8") as f:
                f.write(translation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving translation: {str(e)}")
    
    return {
        "file_id": file_id,
        "translated_file_path": translated_file_path,
        "original_text": text_content,
        "translated_text": translation,
        "document_analysis": document_analysis,
        "quality_review": quality_review
    }

def extract_json(text):
    """Extract JSON from Claude's response"""
    try:
        # Try to find JSON content between triple backticks
        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            json_str = text[json_start:json_end].strip()
        # Try to find JSON content between regular backticks
        elif "```" in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            json_str = text[json_start:json_end].strip()
        # Assume the entire text is JSON
        else:
            json_str = text.strip()
            
        return json.loads(json_str)
    except Exception as e:
        print(f"Error extracting JSON: {str(e)}")
        try:
            # Try to parse the entire text as JSON as a fallback
            return json.loads(text.strip())
        except:
            return {}

@app.get("/api/download/{file_id}")
async def download_file(file_id: str):
    """Get the translated file for download"""
    
    files = os.listdir("temp")
    translated_file_path = None
    
    for f in files:
        if f.startswith(file_id) and "_translated" in f:
            translated_file_path = f"temp/{f}"
            break
    
    if not translated_file_path:
        raise HTTPException(status_code=404, detail="Translated file not found")
    
    return {"file_path": translated_file_path}

@app.post("/api/chat")
async def chat_with_document(chat_request: ChatRequest):
    """Chat about document content using Claude"""
    
    file_id = chat_request.file_id
    query = chat_request.query
    history = chat_request.history
    
    # Find the file for context
    files = os.listdir("temp")
    file_path = None
    translated_file_path = None
    
    for f in files:
        if f.startswith(file_id) and "_translated" not in f:
            file_path = f"temp/{f}"
        elif f.startswith(file_id) and "_translated" in f:
            translated_file_path = f"temp/{f}"
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Extract text for context
    file_extension = file_path.split('.')[-1].lower()
    original_text = ""
    translated_text = ""
    
    try:
        if file_extension == "docx":
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
                original_text = result.value
            
            if translated_file_path:
                with open(translated_file_path, "rb") as docx_file:
                    result = mammoth.extract_raw_text(docx_file)
                    translated_text = result.value
        elif file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                original_text = f.read()
            
            if translated_file_path:
                with open(translated_file_path, "r", encoding="utf-8") as f:
                    translated_text = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    
    # Format chat history for Claude
    formatted_history = ""
    if history:
        for message in history:
            role = message.get("role", "")
            content = message.get("content", "")
            if role == "user":
                formatted_history += f"Human: {content}\n\n"
            elif role == "assistant":
                formatted_history += f"Assistant: {content}\n\n"
    
    # Use Claude to respond with document context
    context = f"""Original document content: 
{original_text[:4000]}  # Truncate to prevent exceeding token limits

Translated content:
{translated_text[:4000] if translated_text else "Not available"}"""
    
    prompt = f"""The user is asking about a document that may have been translated.
Here is the context information about the document:

{context}

Previous conversation:
{formatted_history}

User's question: {query}

Please answer the user's question based on the document content."""
    
    try:
        response = call_claude(
            prompt=prompt,
            system="You are a helpful assistant that answers questions about documents and their translations.",
            max_tokens=2000,
            temperature=0.3
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Main entry point to run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
import mammoth
import os
import uuid
import docx
import json
from pydantic import BaseModel

app = FastAPI()

# Initialize AWS Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'  # Change to your preferred AWS region
)

class TranslationRequest(BaseModel):
    text: str
    source_language: str = "English"
    target_language: str = "French"

class ChatRequest(BaseModel):
    message: str
    file_id: str = None

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
        buffer.write(await file.read())
    
    # Extract text based on file type
    text_content = ""
    try:
        if file_extension == "docx":
            # Handle Word documents
            result = mammoth.extract_raw_text(file_path)
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

@app.post("/api/translate")
async def translate_document(file_id: str, target_language: str = "French"):
    """Translate document content using Claude"""
    
    # Find the file
    files = os.listdir("temp")
    file_path = None
    for f in files:
        if f.startswith(file_id):
            file_path = f"temp/{f}"
            break
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Extract text
    file_extension = file_path.split('.')[-1].lower()
    text_content = ""
    
    try:
        if file_extension == "docx":
            result = mammoth.extract_raw_text(file_path)
            text_content = result.value
        elif file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
    
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
            temperature=0.3
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")
    
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
        "translated_text": translation
    }

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
    
    if not chat_request.file_id:
        # General chatbot without file context
        try:
            response = call_claude(
                prompt=chat_request.message,
                max_tokens=1000
            )
            return {"response": response}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
    
    # Find the file for context
    files = os.listdir("temp")
    file_path = None
    translated_file_path = None
    
    for f in files:
        if f.startswith(chat_request.file_id) and "_translated" not in f:
            file_path = f"temp/{f}"
        elif f.startswith(chat_request.file_id) and "_translated" in f:
            translated_file_path = f"temp/{f}"
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Extract text for context
    file_extension = file_path.split('.')[-1].lower()
    original_text = ""
    translated_text = ""
    
    try:
        if file_extension == "docx":
            result = mammoth.extract_raw_text(file_path)
            original_text = result.value
            if translated_file_path:
                result = mammoth.extract_raw_text(translated_file_path)
                translated_text = result.value
        elif file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                original_text = f.read()
            if translated_file_path:
                with open(translated_file_path, "r", encoding="utf-8") as f:
                    translated_text = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    
    # Use Claude to respond with document context
    context = f"""Original document content: 
{original_text}

Translated content:
{translated_text}"""
    
    prompt = f"""The user is asking about a document that has been translated from English to French.
Here is the context information about the document:

{context}

User's question: {chat_request.message}

Please answer the user's question based on the document content."""
    
    try:
        response = call_claude(
            prompt=prompt,
            system="You are a helpful assistant that answers questions about translated documents.",
            max_tokens=2000,
            temperature=0.3
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

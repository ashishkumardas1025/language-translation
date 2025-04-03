import os
import json
import boto3
from botocore.exceptions import ClientError
import urllib3
from typing import Dict, Any, Optional, Union
import warnings

# Configure warnings and disable insecure request warnings
warnings.filterwarnings("ignore", category=UserWarning, message="Unverified HTTPS request")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Model configuration
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet model ID

def initialize_bedrock_client():
    """Initialize and return AWS Bedrock client with credentials from environment variables"""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")

    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token
    )

    bedrock = session.client(service_name='bedrock-runtime', region_name='us-east-1', verify=False)
    return bedrock

def invoke_bedrock_claude(
    prompt: str, 
    system: Optional[str] = None, 
    max_tokens: int = 512, 
    temperature: float = 0.1
) -> str:
    """Invoke Claude model through AWS Bedrock"""
    bedrock = initialize_bedrock_client()
    
    request_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
    }
    
    if system:
        request_payload["system"] = system
        
    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_payload).encode("utf-8")
        )
        response_body = json.loads(response["body"].read().decode("utf-8"))
        return response_body["content"][0]["text"]
    except ClientError as e:
        print(f"AWS Error: Cannot invoke '{MODEL_ID}'. Reason: {e}")
        raise
    except Exception as e:
        print(f"General Error: {e}")
        raise

def extract_json(text: str) -> Dict:
    """Extract JSON from Claude's response"""
    try:
        # Look for JSON pattern
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            return json.loads(json_str)
        else:
            return {"raw_response": text}
    except json.JSONDecodeError:
        return {"raw_response": text}

def analyze_document(text_content: str) -> Dict[str, Any]:
    """Analyze document structure and content with Quebec French translation in mind"""
    if not text_content:
        return {"error": "No text content provided"}
    
    system_prompt = """You are a document analysis expert specializing in content that will be translated 
    to Quebec French (Canadian French). Your task is to analyze the document's structure and provide insights 
    about its format, content type, sections, and any special formatting that needs to be preserved during 
    translation. Pay special attention to elements that might require adaptation for Quebec cultural context."""
    
    analysis_prompt = f"""Please analyze the following document content with Quebec French translation in mind:

{text_content[:10000]}  # Limit to first 10000 chars for the analysis

Provide the following information in JSON format:
1. Document type (formal, informal, technical, creative, etc.)
2. Content sections (introduction, body, conclusion, etc.)
3. Special formatting elements (tables, lists, headers, etc.)
4. Technical terminology that should be preserved or properly localized to Quebec French
5. Cultural references that might need adaptation for Quebec audiences
6. English expressions that have specific Quebec French equivalents
7. Overall complexity level for translation (low, medium, high)
"""
    
    analysis_result = invoke_bedrock_claude(analysis_prompt, system_prompt, max_tokens=4000)
    analysis_data = extract_json(analysis_result)
    
    return {
        "document_analysis": analysis_data,
        "text_content": text_content
    }

def create_quebec_french_glossary() -> Dict[str, str]:
    """Create a glossary of common terms specific to Quebec French"""
    
    system_prompt = """You are a Quebec French language specialist. Your task is to create a comprehensive 
    glossary of terms that differ between International French and Quebec French."""
    
    glossary_prompt = """Create a glossary of common terms that differ between International French and 
    Quebec French. Include technical terms, common expressions, and everyday vocabulary. Format the response 
    as a JSON object where keys are English terms and values are their Quebec French equivalents.

    Focus on terms that:
    1. Are uniquely Québécois
    2. Have different meanings or usages in Quebec vs. International French
    3. Represent important cultural concepts in Quebec
    4. Are commonly used in business, technology, and everyday communication

    Return only the JSON object without additional explanation."""
    
    glossary_result = invoke_bedrock_claude(glossary_prompt, system_prompt, max_tokens=4000)
    glossary_data = extract_json(glossary_result)
    
    return glossary_data

def translate_document_to_quebec_french(
    text_content: str, 
    document_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Translate document content to Quebec French while preserving formatting and style"""
    if not text_content:
        return {"error": "No text content provided"}
    
    # Create a specialized system prompt based on document analysis
    doc_type = document_analysis.get("document_type", "unknown")
    complexity = document_analysis.get("complexity_level", "medium")
    technical_terms = document_analysis.get("technical_terminology", [])
    cultural_refs = document_analysis.get("cultural_references", [])
    
    # Build system prompt based on analysis
    system_prompt = f"""You are an expert Quebec French translator specialized in {doc_type} documents with {complexity} 
    complexity. You are translating for a Quebec audience and must use Quebec French vocabulary, expressions, and grammar 
    patterns. Translate accurately while preserving the original formatting, tone, and style.
    
    Important Quebec French translation guidelines:
    1. Use Quebec French terminology and expressions rather than International French
    2. Apply Quebec grammar conventions (including contractions like "y'a" instead of "il y a" in informal contexts)
    3. Use Quebec idioms and colloquialisms where appropriate for the context
    4. Adapt cultural references for a Quebec audience
    5. For technical content, use terms familiar to Quebec professionals in that field
    6. Preserve the original formatting, paragraph structure, and style
    7. For informal content, consider using appropriate joual expressions if the context allows it"""
    
    # Add technical terms glossary if available
    technical_terms_str = ""
    if technical_terms:
        if isinstance(technical_terms, list):
            technical_terms_str = "Technical terms to localize to Quebec French:\n" + "\n".join(technical_terms)
        else:
            technical_terms_str = f"Technical terms to localize to Quebec French:\n{technical_terms}"
    
    # Add cultural references note if available
    cultural_refs_str = ""
    if cultural_refs:
        if isinstance(cultural_refs, list):
            cultural_refs_str = "\nCultural references to adapt for Quebec audience:\n" + "\n".join(cultural_refs)
        else:
            cultural_refs_str = f"\nCultural references to adapt for Quebec audience:\n{cultural_refs}"
    
    # Get Quebec French glossary
    quebec_glossary = create_quebec_french_glossary()
    glossary_str = "\nQuebec French vocabulary guidelines:\n" + json.dumps(quebec_glossary, indent=2)
    
    translation_prompt = f"""Please translate the following text from English to Quebec French (Canadian French). 
This translation is specifically intended for a Quebec audience, not a general French-speaking audience.

{technical_terms_str}
{cultural_refs_str}
{glossary_str}

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
    translated_text: str
) -> Dict[str, Any]:
    """Verify Quebec French translation quality and make corrections if needed"""
    if not original_text or not translated_text:
        return {"error": "Missing original or translated text"}
    
    system_prompt = """You are an expert Quebec French reviewer with deep knowledge of Quebec language and culture. 
    Your task is to review translations for accuracy, fluency, and whether they properly reflect Quebec French 
    rather than International French. You should identify any terms or expressions that sound like International 
    French and provide Quebec alternatives."""
    
    # For long texts, check a sample of the beginning, middle and end
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

Please provide:
1. Overall quality assessment (1-10)
2. Quebec French authenticity (1-10, where 10 means perfectly Quebec French)
3. Accuracy assessment (1-10)
4. Fluency assessment (1-10)
5. Style preservation assessment (1-10)
6. International French terms that should be replaced with Quebec equivalents
7. Cultural adaptations assessment
8. Suggested corrections to make the text more authentically Quebec French

Respond in JSON format.
"""
    else:
        review_prompt = f"""Review the quality of this translation from English to Quebec French.

ORIGINAL TEXT:
{original_text}

TRANSLATION:
{translated_text}

Please provide:
1. Overall quality assessment (1-10)
2. Quebec French authenticity (1-10, where 10 means perfectly Quebec French)
3. Accuracy assessment (1-10)
4. Fluency assessment (1-10)
5. Style preservation assessment (1-10)
6. International French terms that should be replaced with Quebec equivalents
7. Cultural adaptations assessment
8. Suggested corrections to make the text more authentically Quebec French

Respond in JSON format.
"""
    
    review_result = invoke_bedrock_claude(review_prompt, system_prompt, max_tokens=4000)
    review_data = extract_json(review_result)
    
    # If quality is low or Quebec French authenticity is low, make corrections
    overall_quality = review_data.get("overall_quality", 0)
    quebec_authenticity = review_data.get("quebec_french_authenticity", 0)
    
    if isinstance(overall_quality, str):
        try:
            overall_quality = int(overall_quality)
        except ValueError:
            overall_quality = 0
            
    if isinstance(quebec_authenticity, str):
        try:
            quebec_authenticity = int(quebec_authenticity)
        except ValueError:
            quebec_authenticity = 0
    
    final_translation = translated_text
    
    # If quality is below 7 or Quebec authenticity is below 8, try to improve the translation
    if (overall_quality < 7 or quebec_authenticity < 8) and "suggested_corrections" in review_data:
        correction_prompt = f"""Please correct the following translation based on these issues to make it more authentic Quebec French:

ORIGINAL TEXT:
{original_text}

CURRENT TRANSLATION:
{translated_text}

ISSUES IDENTIFIED:
International French terms: {json.dumps(review_data.get("international_french_terms", "No specific terms identified"))}

SUGGESTED CORRECTIONS:
{json.dumps(review_data.get("suggested_corrections", "No corrections suggested"))}

Please provide the improved Quebec French translation:
"""
        
        improved_translation = invoke_bedrock_claude(
            prompt=correction_prompt, 
            system=system_prompt, 
            max_tokens=min(100000, len(translated_text) * 2)
        )
        final_translation = improved_translation
    
    return {
        "translated_text": final_translation,
        "quality_review": review_data
    }

def enhance_quebec_french_translation(
    original_text: str, 
    translated_text: str
) -> str:
    """Enhance translation for Quebec French localization, idioms, and cultural nuances"""
    if not translated_text:
        return translated_text
    
    system_prompt = """You are an expert in Quebec French localization and cultural adaptation. Your task is to 
    enhance translations to make them culturally authentic and linguistically appropriate for a Quebec audience.
    You understand the nuances between International French vs. Quebec French, including vocabulary differences, 
    grammar patterns, expressions, and cultural references."""
    
    enhancement_prompt = f"""Enhance the following translation to better match Quebec French regional dialect, expressions, 
    and cultural nuances:
    
    ORIGINAL TEXT:
    {original_text}
    
    CURRENT TRANSLATION:
    {translated_text}
    
    Make the following enhancements:
    1. Replace any International French terms with Quebec French equivalents
    2. Add Quebec-specific expressions where appropriate
    3. Adjust any cultural references to resonate with a Quebec audience
    4. Ensure grammar patterns follow Quebec French conventions
    5. Make the text sound natural to Quebec French speakers
    
    Provide an improved translation that sounds authentically Quebec French:"""
    
    enhanced_translation = invoke_bedrock_claude(
        prompt=enhancement_prompt, 
        system=system_prompt, 
        max_tokens=min(100000, len(translated_text) * 2)
    )
    
    return enhanced_translation

def process_document_for_quebec_french(
    text_content: str,
    quality_threshold: int = 7
) -> Dict[str, Any]:
    """Run the complete Quebec French translation workflow"""
    
    # Step 1: Document analysis
    analysis_result = analyze_document(text_content)
    
    if "error" in analysis_result:
        return {"error": analysis_result["error"], "stage": "document_analysis"}
    
    # Step 2: Quebec French translation
    translation_result = translate_document_to_quebec_french(
        text_content, 
        analysis_result.get("document_analysis", {})
    )
    
    if "error" in translation_result:
        return {"error": translation_result["error"], "stage": "translation"}
    
    # Step 3: Quebec French quality check
    quality_result = check_quebec_french_quality(
        text_content,
        translation_result.get("translated_text", "")
    )
    
    if "error" in quality_result:
        return {"error": quality_result["error"], "stage": "quality_check"}
    
    # Step 4: Quebec French enhancement
    enhanced_translation = enhance_quebec_french_translation(
        text_content,
        quality_result.get("translated_text", "")
    )
    
    # Return the final result
    return {
        "original_text": text_content,
        "translated_text": enhanced_translation,
        "document_analysis": analysis_result.get("document_analysis", {}),
        "quality_review": quality_result.get("quality_review", {}),
        "target_language": "Quebec French"
    }

def batch_translate_to_quebec_french(
    documents: Dict[str, str]
) -> Dict[str, Dict[str, Any]]:
    """Process multiple documents in batch for Quebec French translation"""
    results = {}
    
    for doc_name, content in documents.items():
        print(f"Processing document for Quebec French translation: {doc_name}")
        results[doc_name] = process_document_for_quebec_french(content)
        
    return results

# Main execution block
if __name__ == "__main__":
    try:
        # Example usage
        sample_text = """This is a sample text to translate.
        It contains multiple lines and paragraphs.
        
        This is a new paragraph with some technical terms like machine learning and artificial intelligence."""
        
        result = process_document_for_quebec_french(sample_text)
        print("Quebec French translation completed successfully!")
        print(f"Original length: {len(result['original_text'])}")
        print(f"Translated length: {len(result['translated_text'])}")
        print("\nQuebec French translated text sample:")
        print(result['translated_text'][:200] + "...")
        
    except Exception as e:
        print(f"Quebec French translation process failed: {e}")
        exit(1)

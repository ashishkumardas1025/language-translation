import os
import json
import boto3
from botocore.exceptions import ClientError
import urllib3
from typing import Dict, Any, Optional, Union
import warnings
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

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
    2. Apply Quebec grammar conventions (including contractions like "y'a" instead of "il y a" in informal contexts)
    3. Use Quebec idioms and colloquialisms where appropriate for the context
    4. Preserve the original formatting, paragraph structure, and style
    5. For informal content, consider using appropriate joual expressions if the context allows it"""
    
    # Format custom terminology if provided
    custom_terms_str = ""
    if custom_terms:
        custom_terms_str = "\nCustom banking terminology to use (always use these specific translations):\n" + json.dumps(custom_terms, indent=2)
    
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
    """Verify Quebec French translation quality and make corrections if needed"""
    if not original_text or not translated_text:
        return {"error": "Missing original or translated text"}
    
    system_prompt = """You are an expert Quebec French reviewer with deep knowledge of Quebec language and culture. 
    Your task is to review translations for accuracy, fluency, and whether they properly reflect Quebec French 
    rather than International French. You should identify any terms or expressions that sound like International 
    French and provide Quebec alternatives."""
    
    # Add custom terminology to review criteria
    custom_terms_str = ""
    if custom_terms:
        custom_terms_str = "\nCustom banking terminology that MUST be used (check if these exact translations are used):\n" + json.dumps(custom_terms, indent=2)
    
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
{custom_terms_str}

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
5. International French terms that should be replaced with Quebec equivalents
6. Custom terminology compliance (verify that all custom banking terms were translated correctly)
7. Suggested corrections to make the text more authentically Quebec French

Respond in JSON format.
"""
    else:
        review_prompt = f"""Review the quality of this translation from English to Quebec French.
{custom_terms_str}

ORIGINAL TEXT:
{original_text}

TRANSLATION:
{translated_text}

Please provide:
1. Overall quality assessment (1-10)
2. Quebec French authenticity (1-10, where 10 means perfectly Quebec French)
3. Accuracy assessment (1-10)
4. Fluency assessment (1-10)
5. International French terms that should be replaced with Quebec equivalents
6. Custom terminology compliance (verify that all custom banking terms were translated correctly)
7. Suggested corrections to make the text more authentically Quebec French

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
{custom_terms_str}

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

def calculate_cosine_similarity(text1, text2):
    """Calculate cosine similarity between two texts"""
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except:
        return 0.0

# Main execution block
if __name__ == "__main__":
    try:
        # Example usage with custom banking terminology
        custom_banking_terms = {
            "help": "aide",
            "sign out": "quitter",
            "account": "compte",
            "balance": "solde",
            "transfer": "virement"
        }
        
        sample_text = """This is a sample text to translate.
        It contains multiple lines and paragraphs with banking terms like help, sign out, account, and balance.
        
        This is a new paragraph with some technical terms."""
        
        result = process_document_for_quebec_french(sample_text, custom_banking_terms)
        print("Quebec French translation completed successfully!")
        print(f"Original length: {len(result['original_text'])}")
        print(f"Translated length: {len(result['translated_text'])}")
        print("\nQuebec French translated text sample:")
        print(result['translated_text'][:200] + "...")
        
    except Exception as e:
        print(f"Quebec French translation process failed: {e}")
        exit(1)





#####################################################

def assess_semantic_accuracy(
    generated_text: str,
    reference_text: str,
    custom_terms: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Use Claude to assess semantic accuracy between generated and reference translations
    by comparing meaning preservation, tone, and Quebec French authenticity.
    """
    if not generated_text or not reference_text:
        return {"error": "Missing generated or reference text"}
    
    system_prompt = """You are an expert Quebec French linguistic evaluator with deep knowledge of Quebec language, 
    culture, and linguistic nuances. Your task is to compare a machine-generated Quebec French translation with a 
    reference human translation, evaluating how well the machine translation captures the meaning, tone, and Quebec-specific 
    language features of the reference."""
    
    # Format custom terminology if provided
    custom_terms_str = ""
    if custom_terms:
        custom_terms_str = "\nThe following custom banking terminology should be used in the translation:\n" + json.dumps(custom_terms, indent=2)
    
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
{custom_terms_str}

MACHINE-GENERATED TRANSLATION (SAMPLES):
Beginning: {gen_samples[0]}

Middle: {gen_samples[1]}

End: {gen_samples[2]}

REFERENCE HUMAN TRANSLATION (SAMPLES):
Beginning: {ref_samples[0]}

Middle: {ref_samples[1]}

End: {ref_samples[2]}

Please evaluate the semantic accuracy of the machine-generated translation compared to the reference. Provide:

1. Semantic Accuracy Score (1-10): How well the generated translation preserves the meaning of the reference translation
2. Quebec French Authenticity Comparison (1-10): How the generated translation compares to the reference in terms of authentic Quebec French expressions and terminology
3. Fluency Comparison (1-10): How natural the generated translation sounds compared to the reference
4. Terminology Consistency Score (1-10): How consistently banking/domain terminology is used compared to the reference
5. Key differences: Identify major semantic differences (meaning changes or losses)
6. Missing Quebec expressions: Quebec French expressions in the reference that are missing from the generated text
7. Strengths: What the generated translation does well compared to the reference
8. Overall assessment: A brief 2-3 sentence summary of how the generated translation compares to the reference

Respond in JSON format.
"""
    else:
        assessment_prompt = f"""Compare the following machine-generated Quebec French translation with the reference human translation.
{custom_terms_str}

MACHINE-GENERATED TRANSLATION:
{generated_text}

REFERENCE HUMAN TRANSLATION:
{reference_text}

Please evaluate the semantic accuracy of the machine-generated translation compared to the reference. Provide:

1. Semantic Accuracy Score (1-10): How well the generated translation preserves the meaning of the reference translation
2. Quebec French Authenticity Comparison (1-10): How the generated translation compares to the reference in terms of authentic Quebec French expressions and terminology
3. Fluency Comparison (1-10): How natural the generated translation sounds compared to the reference
4. Terminology Consistency Score (1-10): How consistently banking/domain terminology is used compared to the reference
5. Key differences: Identify major semantic differences (meaning changes or losses)
6. Missing Quebec expressions: Quebec French expressions in the reference that are missing from the generated text
7. Strengths: What the generated translation does well compared to the reference
8. Overall assessment: A brief 2-3 sentence summary of how the generated translation compares to the reference

Respond in JSON format.
"""
    
    assessment_result = invoke_bedrock_claude(assessment_prompt, system_prompt, max_tokens=4000)
    assessment_data = extract_json(assessment_result)
    
    return assessment_data

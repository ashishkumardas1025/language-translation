import os
import json
import boto3
from botocore.exceptions import ClientError
import urllib3
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, message="Unverified HTTPS request")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def initialize_bedrock_client():
    """Initialize and return an AWS Bedrock client."""
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

def invoke_bedrock_claude(prompt: str, max_tokens: int = 2048, temperature: float = 0.1):
    """Invoke Claude model on AWS Bedrock."""
    MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1.0"

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
        print(f"AWS Error: Cannot Invoke '{MODEL_ID}' Reason: {e}")
        raise
    except Exception as e:
        print(f"General Error: {e}")
        raise

def translate_to_canadian_french(text):
    """Translate text to Canadian French using Claude."""
    translation_prompt = f"""Please translate the following text to Canadian French (French as spoken in Quebec, not European French). 
Maintain the same formatting, paragraph breaks, and sentence structure. Keep any technical terms intact where appropriate.
If there are Canadian French specific terms or expressions that would be more appropriate than standard French translations, please use those.

Text to translate:
{text}

Translation:"""

    try:
        translated_text = invoke_bedrock_claude(translation_prompt)
        return translated_text
    except Exception as e:
        print(f"Translation failed: {e}")
        return None

def translate_file(file_path):
    """Translate content of a file to Canadian French."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        translated_content = translate_to_canadian_french(content)
        
        # Create output file path with _fr-CA suffix
        file_name, file_ext = os.path.splitext(file_path)
        output_path = f"{file_name}_fr-CA{file_ext}"
        
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(translated_content)
        
        return output_path
    except Exception as e:
        print(f"File translation failed: {e}")
        return None

if __name__ == "__main__":
    try:
        # Example usage
        sample_text = "Welcome to our service. Please let us know if you need any assistance."
        translated = translate_to_canadian_french(sample_text)
        print(f"Original: {sample_text}")
        print(f"Translated: {translated}")
        
        # Example file translation
        # translate_file("sample.txt")
    except Exception as e:
        print(f"Failed to get response: {e}")
        exit(1)

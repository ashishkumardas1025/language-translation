import json
import os
import time
import boto3
from botocore.exceptions import ClientError
import urllib3
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message="Unverified HTTPS request")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def initialize_bedrock_client():
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

def invoke_bedrock_claude(prompt: str, max_tokens: int = 512, temperature: float = 0.1):
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

class MainframeAnalyzer:
    def __init__(self, output_dir="output"):
        """
        Initialize the MainframeAnalyzer with output settings
        
        Args:
            output_dir (str): Directory to save output documents
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            os.makedirs(os.path.join(output_dir, "individual"))
            
        print(f"Initialized MainframeAnalyzer")

    def analyze_file(self, file_type, file_name, file_content):
        """
        Analyze an individual mainframe file
        
        Args:
            file_type (str): Type of file (JCL, PROC, CLIST, etc.)
            file_name (str): Name of the file
            file_content (str): Content of the file
            
        Returns:
            str: Technical documentation for the file
        """
        print(f"Analyzing {file_type} file: {file_name}")
        
        prompt = f"""
        You are analyzing a mainframe routing system component. This is a {file_type} file named {file_name}.
        
        Here is the content of the file:
        ```
        {file_content}
        ```
        
        Create detailed technical documentation for this file including:
        1. Purpose and function of this component
        2. Input/output parameters
        3. Key functionality and logic flow
        4. Dependencies on other components (if any)
        5. Any error handling or special conditions
        
        Focus on technical details and be specific. Use markdown formatting for better readability.
        """
        
        response = invoke_bedrock_claude(prompt, max_tokens=4096, temperature=0.1)
        
        # Save individual analysis
        output_path = os.path.join(self.output_dir, "individual", f"{file_name}_analysis.md")
        with open(output_path, 'w') as f:
            f.write(response)
            
        return response

    def generate_comprehensive_document(self, individual_analyses):
        """
        Generate a comprehensive technical document based on all individual analyses
        
        Args:
            individual_analyses (dict): Dictionary mapping file names to their analyses
            
        Returns:
            str: Comprehensive technical document
        """
        print("Generating comprehensive technical document")
        
        # Prepare the prompt with information about the system and individual analyses
        file_descriptions = "\n\n".join([
            f"### {file_name}\n{analysis}" 
            for file_name, analysis in individual_analyses.items()
        ])
        
        prompt = f"""
        You are analyzing a mainframe routing system with multiple components. Below are technical analyses of individual components. 
        
        Your task is to create a comprehensive technical document that shows the entire system, component relationships, and data flows.
        
        Here is the high-level flow of the system: 
        JCL["FTFJOB-JCL.txt"] -> PROC["FTFOUT-PROC.txt"] -> CLIST["FTFOUT-CLIST.txt"] -> COBOL["FTFOUT_COBOL.txt"] -> Assembler["FTFOUTIO-Assembler.txt"]
        
        Important relationships:
        - FTFOUT COBOL program calls FTFOUTIO Assembler and FTFOUTTL COBOL
        - FTFOUTIO Assembler program calls FTFOUTMG COBOL
        - COPYBOOKS are used by multiple COBOL programs:
          - FTFCWCMP-COPYBOOK.txt used by: FTFOUT, FTFOUTTL, FTFOUTMG
          - FTFOUTIC-COPYBOOK.txt used by: FTFOUT, FTFOUTTL
          - FTFPWCMP-COPYBOOK.txt used by: FTFOUT, FTFOUTTL, FTFOUTMG
        
        Individual component analyses:
        {file_descriptions}
        
        Create a comprehensive technical document that includes:
        1. Executive summary of the entire system
        2. System architecture and component relationships
        3. Data flow diagrams (described in text)
        4. Detailed component interactions
        5. Technical requirements based on the analysis
        6. Functional requirements based on the analysis
        
        Focus on providing a clear understanding of how the entire system works together, with special attention to component interactions and dependencies.
        """
        
        response = invoke_bedrock_claude(prompt, max_tokens=8192, temperature=0.1)
        
        # Save comprehensive document
        output_path = os.path.join(self.output_dir, "comprehensive_technical_document.md")
        with open(output_path, 'w') as f:
            f.write(response)
            
        return response

    def run_analysis_pipeline(self, file_data):
        """
        Run the complete analysis pipeline
        
        Args:
            file_data (dict): Dictionary containing file data by type and name
            
        Returns:
            str: Path to the comprehensive technical document
        """
        print("Starting analysis pipeline")
        
        individual_analyses = {}
        
        # Process each file type
        for file_type, files in file_data.items():
            for file_name, file_content in files.items():
                analysis = self.analyze_file(file_type, file_name, file_content)
                individual_analyses[file_name] = analysis
                # Add a small delay to avoid rate limiting
                time.sleep(1)
        
        # Generate comprehensive document
        comprehensive_doc = self.generate_comprehensive_document(individual_analyses)
        
        print(f"Analysis pipeline completed. Output saved to {self.output_dir}")
        return os.path.join(self.output_dir, "comprehensive_technical_document.md")


def main():
    """
    Main function to run the mainframe analysis
    """
    # Sample file data - in a real scenario, this would be loaded from actual files
    # For this example, we'll use placeholder content
    file_data = {
        "JCL": {
            "FTFJOB-JCL.txt": "/* Sample JCL content - would be loaded from actual file */"
        },
        "PROC": {
            "FTFOUT-PROC.txt": "/* Sample PROC content - would be loaded from actual file */"
        },
        "CLIST": {
            "FTFOUT-CLIST.txt": "/* Sample CLIST content - would be loaded from actual file */"
        },
        "COBOL": {
            "FTFOUT_COBOL.txt": "/* Sample COBOL content - would be loaded from actual file */",
            "FTFOUTTL-COBOL.txt": "/* Sample COBOL content - would be loaded from actual file */",
            "FTFOUTMG-COBOL.txt": "/* Sample COBOL content - would be loaded from actual file */"
        },
        "Assembler": {
            "FTFOUTIO-Assembler.txt": "/* Sample Assembler content - would be loaded from actual file */"
        },
        "COPYBOOK": {
            "FTFCWCMP-COPYBOOK.txt": "/* Sample COPYBOOK content - would be loaded from actual file */",
            "FTFOUTIC-COPYBOOK.txt": "/* Sample COPYBOOK content - would be loaded from actual file */",
            "FTFPWCMP-COPYBOOK.txt": "/* Sample COPYBOOK content - would be loaded from actual file */"
        }
    }
    
    # In a real implementation, you would load the actual file contents:
    # file_data = load_files_from_directory('path/to/mainframe/files')
    
    analyzer = MainframeAnalyzer()
    doc_path = analyzer.run_analysis_pipeline(file_data)
    
    print(f"Analysis complete. Comprehensive document saved to: {doc_path}")


def load_files_from_directory(base_dir):
    """
    Load files from the directory structure
    
    Args:
        base_dir (str): Base directory containing the mainframe files
        
    Returns:
        dict: Dictionary with file contents organized by type
    """
    file_data = {
        "JCL": {},
        "PROC": {},
        "CLIST": {},
        "COBOL": {},
        "Assembler": {},
        "COPYBOOK": {}
    }
    
    # Map directories to file types
    dir_to_type = {
        "JCL": "JCL",
        "PROC": "PROC",
        "CLIST": "CLIST",
        "COBOL": "COBOL",
        "Assembler": "Assembler",
        "Copybook": "COPYBOOK"
    }
    
    # Files to focus on based on requirements
    focus_files = [
        "FTFJOB-JCL.txt",
        "FTFOUT-PROC.txt",
        "FTFOUT-CLIST.txt",
        "FTFOUT_COBOL.txt",
        "FTFOUTTL-COBOL.txt",
        "FTFOUTMG-COBOL.txt",
        "FTFOUTIO-Assembler.txt",
        "FTFCWCMP-COPYBOOK.txt",
        "FTFOUTIC-COPYBOOK.txt",
        "FTFPWCMP-COPYBOOK.txt"
    ]
    
    # Walk through the directory structure
    for root, dirs, files in os.walk(base_dir):
        dir_name = os.path.basename(root)
        
        if dir_name in dir_to_type:
            file_type = dir_to_type[dir_name]
            
            for file in files:
                if file in focus_files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            file_data[file_type][file] = content
                            print(f"Loaded {file_type} file: {file}")
                    except Exception as e:
                        print(f"Error loading file {file_path}: {e}")
    
    return file_data


if __name__ == "__main__":
    main()

import json
import boto3
from botocore.exceptions import ClientError
import urllib3
from typing import Dict, Any, Optional, Union, List, Tuple
import warnings
import os
import pandas as pd
import glob
from pathlib import Path
import re
from dataclasses import dataclass
from collections import defaultdict

# Configure warnings and disable insecure request warnings
warnings.filterwarnings("ignore", category=UserWarning, message="Unverified HTTPS request")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Model configuration
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet model ID

@dataclass
class CapabilityMatch:
    """Data class to store capability match information"""
    capability_name: str
    scope_description: str
    file_path: str
    sheet_name: str
    confidence_score: float
    additional_context: Dict[str, Any] = None

class CapabilitySearchEngine:
    def __init__(self, sample_estimations_directory: str):
        """Initialize the capability search engine"""
        self.directory = sample_estimations_directory
        self.bedrock_client = None
        self.capabilities_data = []
        
    def initialize_bedrock_client(self):
        """Initialize and return AWS Bedrock client with credentials from environment variables"""
        if self.bedrock_client is None:
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")

            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token
            )

            self.bedrock_client = session.client(
                service_name='bedrock-runtime', 
                region_name='us-east-1', 
                verify=False
            )
        return self.bedrock_client

    def invoke_bedrock_claude(
        self, 
        prompt: str, 
        system: Optional[str] = None, 
        max_tokens: int = 1000, 
        temperature: float = 0.1
    ) -> str:
        """Invoke Claude model through AWS Bedrock"""
        bedrock = self.initialize_bedrock_client()
        
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

    def load_excel_files(self) -> List[str]:
        """Load all Excel files from the Sample Estimations directory"""
        excel_files = []
        search_patterns = [
            os.path.join(self.directory, "*.xlsx"),
            os.path.join(self.directory, "*.xls"),
            os.path.join(self.directory, "**", "*.xlsx"),
            os.path.join(self.directory, "**", "*.xls")
        ]
        
        for pattern in search_patterns:
            excel_files.extend(glob.glob(pattern, recursive=True))
        
        return list(set(excel_files))  # Remove duplicates

    def extract_capabilities_from_file(self, file_path: str) -> List[CapabilityMatch]:
        """Extract capabilities from a single Excel file"""
        capabilities = []
        file_name = os.path.basename(file_path)
        
        try:
            # Read all sheets to find relevant ones
            xl_file = pd.ExcelFile(file_path)
            sheet_names = xl_file.sheet_names
            
            # Look for relevant sheets (Capability List, Project T-Shirt, etc.)
            relevant_sheets = []
            for sheet in sheet_names:
                sheet_lower = sheet.lower()
                if any(keyword in sheet_lower for keyword in ['capability', 'project', 't-shirt', 'scope']):
                    relevant_sheets.append(sheet)
            
            # If no specific sheets found, try all sheets
            if not relevant_sheets:
                relevant_sheets = sheet_names[:3]  # Limit to first 3 sheets to avoid performance issues
            
            for sheet_name in relevant_sheets:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    capabilities.extend(self._parse_sheet_for_capabilities(df, file_path, sheet_name))
                except Exception as e:
                    print(f"Warning: Could not read sheet '{sheet_name}' from {file_name}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error reading file {file_name}: {e}")
            
        return capabilities

    def _parse_sheet_for_capabilities(self, df: pd.DataFrame, file_path: str, sheet_name: str) -> List[CapabilityMatch]:
        """Parse a DataFrame to extract capabilities and their descriptions"""
        capabilities = []
        
        if df.empty:
            return capabilities
        
        # Common column name patterns to look for
        capability_columns = []
        description_columns = []
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['capability', 'feature', 'function', 'requirement']):
                capability_columns.append(col)
            elif any(keyword in col_lower for keyword in ['description', 'scope', 'business', 'detail']):
                description_columns.append(col)
        
        # If no specific columns found, use heuristics
        if not capability_columns and len(df.columns) > 0:
            # Look for columns that might contain capability names
            for i, col in enumerate(df.columns):
                sample_values = df[col].dropna().head(5).astype(str)
                if any(len(val) > 10 and len(val) < 100 for val in sample_values):
                    capability_columns.append(col)
                    break
        
        if not description_columns and len(df.columns) > 1:
            # Look for columns that might contain descriptions
            for col in df.columns:
                if col not in capability_columns:
                    sample_values = df[col].dropna().head(3).astype(str)
                    if any(len(val) > 20 for val in sample_values):
                        description_columns.append(col)
                        break
        
        # Extract capabilities
        for _, row in df.iterrows():
            for cap_col in capability_columns:
                capability_name = str(row.get(cap_col, '')).strip()
                
                if capability_name and capability_name != 'nan' and len(capability_name) > 3:
                    # Get description from description columns
                    description = ""
                    for desc_col in description_columns:
                        desc_value = str(row.get(desc_col, '')).strip()
                        if desc_value and desc_value != 'nan':
                            description += f"{desc_value} "
                    
                    # If no description found, use other columns as context
                    if not description:
                        for col in df.columns:
                            if col not in capability_columns:
                                val = str(row.get(col, '')).strip()
                                if val and val != 'nan' and len(val) > 10:
                                    description += f"{val} "
                    
                    if description.strip():
                        capabilities.append(CapabilityMatch(
                            capability_name=capability_name,
                            scope_description=description.strip(),
                            file_path=file_path,
                            sheet_name=sheet_name,
                            confidence_score=1.0,  # Will be calculated later
                            additional_context=dict(row)
                        ))
        
        return capabilities

    def calculate_similarity_score(self, search_term: str, capability: CapabilityMatch) -> float:
        """Calculate similarity score between search term and capability"""
        search_lower = search_term.lower()
        cap_lower = capability.capability_name.lower()
        desc_lower = capability.scope_description.lower()
        
        # Exact match in capability name
        if search_lower == cap_lower:
            return 1.0
        
        # Substring match in capability name
        if search_lower in cap_lower or cap_lower in search_lower:
            return 0.8
        
        # Word-level matching
        search_words = set(search_lower.split())
        cap_words = set(cap_lower.split())
        desc_words = set(desc_lower.split())
        
        # Calculate word overlap
        cap_overlap = len(search_words.intersection(cap_words)) / max(len(search_words), len(cap_words))
        desc_overlap = len(search_words.intersection(desc_words)) / max(len(search_words), len(desc_words))
        
        # Combined score
        combined_score = (cap_overlap * 0.7) + (desc_overlap * 0.3)
        
        # Bonus for partial matches
        if any(word in cap_lower for word in search_words):
            combined_score += 0.1
        
        return min(combined_score, 1.0)

    def search_capabilities(self, search_term: str, top_k: int = 3) -> List[CapabilityMatch]:
        """Search for capabilities matching the search term"""
        print(f"Searching for capabilities matching: '{search_term}'")
        print("Loading Excel files...")
        
        # Load all capabilities from Excel files
        excel_files = self.load_excel_files()
        all_capabilities = []
        
        for file_path in excel_files:
            print(f"Processing: {os.path.basename(file_path)}")
            capabilities = self.extract_capabilities_from_file(file_path)
            all_capabilities.extend(capabilities)
        
        print(f"Found {len(all_capabilities)} total capabilities across {len(excel_files)} files")
        
        # Calculate similarity scores
        scored_capabilities = []
        for capability in all_capabilities:
            score = self.calculate_similarity_score(search_term, capability)
            if score > 0.1:  # Only include capabilities with some relevance
                capability.confidence_score = score
                scored_capabilities.append(capability)
        
        # Sort by confidence score
        scored_capabilities.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Return top k results
        return scored_capabilities[:top_k]

    def generate_summary_with_claude(self, search_term: str, matches: List[CapabilityMatch]) -> str:
        """Generate a summary of the capability matches using Claude"""
        if not matches:
            return f"No capabilities found matching '{search_term}'"
        
        # Prepare context for Claude
        context = f"Search Term: {search_term}\n\n"
        context += "Found the following matching capabilities:\n\n"
        
        for i, match in enumerate(matches, 1):
            context += f"Match {i}:\n"
            context += f"- Capability: {match.capability_name}\n"
            context += f"- Source: {os.path.basename(match.file_path)} (Sheet: {match.sheet_name})\n"
            context += f"- Description: {match.scope_description}\n"
            context += f"- Confidence Score: {match.confidence_score:.2f}\n\n"
        
        system_prompt = """You are an expert business analyst specializing in capability analysis. 
        Your task is to provide a comprehensive summary of the capabilities found based on the search term.
        
        Please provide:
        1. A brief overview of what the search term represents
        2. Summary of each matching capability found
        3. Key insights about the capabilities
        4. How these capabilities relate to each other (if applicable)
        
        Keep the summary concise but informative, focusing on business value and functionality."""
        
        user_prompt = f"Based on the following capability search results, provide a comprehensive summary:\n\n{context}"
        
        try:
            summary = self.invoke_bedrock_claude(
                prompt=user_prompt,
                system=system_prompt,
                max_tokens=1500,
                temperature=0.1
            )
            return summary
        except Exception as e:
            return f"Error generating summary with Claude: {e}"

    def interactive_search(self):
        """Interactive terminal interface for capability search"""
        print("=== Capability Search Tool ===")
        print(f"Searching in directory: {self.directory}")
        print("Type 'quit' or 'exit' to stop\n")
        
        while True:
            try:
                search_term = input("Enter capability to search for: ").strip()
                
                if search_term.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if not search_term:
                    print("Please enter a valid search term.")
                    continue
                
                print("\n" + "="*50)
                
                # Search for capabilities
                matches = self.search_capabilities(search_term, top_k=3)
                
                if not matches:
                    print(f"No capabilities found matching '{search_term}'")
                    continue
                
                # Generate summary with Claude
                print("Generating summary with Claude...")
                summary = self.generate_summary_with_claude(search_term, matches)
                
                print("\n=== CAPABILITY SEARCH RESULTS ===")
                print(f"Search Term: {search_term}")
                print(f"Found {len(matches)} matching capabilities\n")
                
                print("=== AI-GENERATED SUMMARY ===")
                print(summary)
                
                print("\n=== DETAILED RESULTS ===")
                for i, match in enumerate(matches, 1):
                    print(f"\n{i}. {match.capability_name}")
                    print(f"   Source: {match.file_path}")
                    print(f"   Sheet: {match.sheet_name}")
                    print(f"   Confidence: {match.confidence_score:.2f}")
                    print(f"   Description: {match.scope_description[:200]}{'...' if len(match.scope_description) > 200 else ''}")
                
                print("\n" + "="*50 + "\n")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue

def main():
    """Main function to run the capability search tool"""
    # Get directory path from user or use default
    directory = input("Enter path to Sample Estimations directory (or press Enter for current directory): ").strip()
    if not directory:
        directory = "."
    
    # Validate directory exists
    if not os.path.exists(directory):
        print(f"Directory '{directory}' does not exist!")
        return
    
    # Initialize and run the search engine
    search_engine = CapabilitySearchEngine(directory)
    search_engine.interactive_search()

if __name__ == "__main__":
    main()

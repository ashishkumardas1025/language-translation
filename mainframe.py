import os
import sys
import argparse
import json
import re
import anthropic
from pathlib import Path

class MainframeCodeDocumenter:
    """A tool to generate comprehensive technical documentation from mainframe code using Claude 3.5 Sonnet."""
    
    def __init__(self, api_key=None, model="claude-3-5-sonnet-20240620"):
        """Initialize the documenter with API credentials and parameters."""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set the ANTHROPIC_API_KEY environment variable or pass it as a parameter.")
        
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Dictionary mapping file extensions to mainframe languages
        self.extension_map = {
            ".asm": "Assembler",
            ".clist": "CLIST", 
            ".cbl": "COBOL",
            ".cpy": "COBOL Copybook",
            ".jcl": "JCL",
            ".proc": "PROC",
            # Add more mappings as needed
        }
        
    def detect_language(self, filename):
        """Detect the mainframe language based on file extension or content analysis."""
        ext = Path(filename).suffix.lower()
        
        # Check if the extension is in our mapping
        if ext in self.extension_map:
            return self.extension_map[ext]
            
        # Attempt content-based detection if extension is unknown
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)  # Read first 1000 characters for analysis
            
            # Simple heuristics for language detection
            if re.search(r'^\s*//\s*EXEC\s+', content, re.MULTILINE):
                return "JCL"
            elif re.search(r'^\s*IDENTIFICATION\s+DIVISION', content, re.MULTILINE):
                return "COBOL"
            elif re.search(r'^\s*PROC\s+\d+\s', content, re.MULTILINE):
                return "PROC"
            elif re.search(r'^\s*CSECT\s+', content, re.MULTILINE):
                return "Assembler"
            
        # Default to generic if detection fails
        return "Unknown Mainframe Code"
    
    def create_prompt(self, code, language):
        """Create a structured prompt for Claude to analyze the code."""
        return f"""Please analyze this {language} code and create a comprehensive technical document. 
The document should be detailed enough for someone to implement the same functionality in a modern language like Python.

# {language} CODE:
```
{code}
```

Please create a complete technical specification with the following sections:

1. OVERVIEW
   - High-level description of what this code does
   - Business purpose and context
   - Main functionality and processing logic

2. INPUT/OUTPUT
   - All inputs (files, parameters, environment variables, databases)
   - All outputs (files, screen displays, databases, return codes)
   - Data formats and structures

3. PROCESSING LOGIC
   - Step-by-step description of the algorithm
   - Business rules and conditions
   - Error handling and special cases
   - Processing sequence and dependencies

4. DATA DICTIONARY
   - All variables, fields, and data structures
   - Data types, sizes, and formats
   - Purpose of each variable
   - Validation rules and constraints

5. CONTROL FLOW
   - Program flow and logic branches
   - Loops and iterations
   - Conditional processing
   - Subroutine calls and relationships

6. TECHNICAL CONSIDERATIONS
   - Performance characteristics
   - Resource requirements
   - Security considerations
   - Environmental dependencies

7. MODERNIZATION GUIDANCE
   - Recommendations for implementation in Python
   - Potential modernization challenges
   - Equivalent modern libraries or frameworks
   - Pseudocode for key algorithms

Format the document with clear headings, bullet points for lists, and tables for structured data where appropriate.
"""
    
    def generate_documentation(self, filename):
        """Generate technical documentation from the provided file."""
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            language = self.detect_language(filename)
            print(f"Detected language: {language}")
            
            prompt = self.create_prompt(code, language)
            
            print(f"Generating documentation for {filename}...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            doc_content = response.content[0].text
            
            # Create output filename
            base_name = Path(filename).stem
            output_file = f"{base_name}_technical_doc.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(doc_content)
            
            print(f"Documentation saved to {output_file}")
            return output_file, doc_content
            
        except Exception as e:
            print(f"Error generating documentation: {str(e)}")
            return None, str(e)
    
    def batch_process(self, directory, extensions=None):
        """Process all matching files in a directory."""
        if extensions is None:
            extensions = list(self.extension_map.keys())
            
        results = []
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    filepath = os.path.join(root, file)
                    output_file, _ = self.generate_documentation(filepath)
                    if output_file:
                        results.append((filepath, output_file))
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Generate technical documentation from mainframe code using Claude 3.5 Sonnet')
    parser.add_argument('file', help='Path to the mainframe code file or directory')
    parser.add_argument('--api-key', help='Anthropic API key (optional if ANTHROPIC_API_KEY environment variable is set)')
    parser.add_argument('--batch', action='store_true', help='Process all matching files in directory')
    parser.add_argument('--model', default="claude-3-5-sonnet-20240620", help='Claude model to use')
    
    args = parser.parse_args()
    
    try:
        documenter = MainframeCodeDocumenter(api_key=args.api_key, model=args.model)
        
        if args.batch and os.path.isdir(args.file):
            results = documenter.batch_process(args.file)
            print(f"Processed {len(results)} files")
            for src, dest in results:
                print(f"{src} -> {dest}")
        else:
            if not os.path.isfile(args.file):
                print(f"Error: {args.file} is not a valid file")
                sys.exit(1)
                
            output_file, doc_content = documenter.generate_documentation(args.file)
            if output_file:
                print("\nSample of generated documentation:")
                print("=" * 80)
                print(doc_content[:500] + "...")
                print("=" * 80)
                print(f"\nFull documentation saved to {output_file}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

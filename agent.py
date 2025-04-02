import boto3
import os
import json
from typing import Dict, Any, List, Optional

class BaseAgent:
    """Base agent class with core functionality"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'  # Change to your preferred AWS region
        )
        self.model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'  # Claude 3.5 Sonnet model ID
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def call_claude(self, prompt: str, system: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 4000) -> str:
        """Helper method to call Claude API via AWS Bedrock"""
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
                
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read().decode('utf-8'))
            return response_body['content'][0]['text']
        except Exception as e:
            print(f"Error calling Claude: {str(e)}")
            return f"Error: {str(e)}"


class DocumentAnalysisAgent(BaseAgent):
    """Agent responsible for analyzing document structure and content"""
    
    def __init__(self):
        super().__init__(
            name="DocumentAnalysisAgent",
            description="Analyzes document structure, format, and content to prepare for translation"
        )
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        text_content = input_data.get("text_content", "")
        
        if not text_content:
            return {"error": "No text content provided"}
        
        system_prompt = """You are a document analysis expert. Your task is to analyze the document's 
        structure and provide insights about its format, content type, sections, and any special 
        formatting that needs to be preserved during translation."""
        
        analysis_prompt = f"""Please analyze the following document content:

{text_content[:10000]}  # Limit to first 10000 chars for the analysis

Provide the following information in JSON format:
1. Document type (formal, informal, technical, creative, etc.)
2. Content sections (introduction, body, conclusion, etc.)
3. Special formatting elements (tables, lists, headers, etc.)
4. Technical terminology that should be preserved
5. Overall complexity level for translation (low, medium, high)
"""
        
        analysis_result = self.call_claude(analysis_prompt, system_prompt)
        
        # Try to extract JSON if present
        try:
            # Look for JSON pattern
            json_start = analysis_result.find('{')
            json_end = analysis_result.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = analysis_result[json_start:json_end]
                analysis_data = json.loads(json_str)
            else:
                analysis_data = {"analysis": analysis_result}
        except json.JSONDecodeError:
            analysis_data = {"analysis": analysis_result}
        
        return {
            "document_analysis": analysis_data,
            "text_content": text_content
        }


class TranslationAgent(BaseAgent):
    """Agent responsible for performing the actual translation"""
    
    def __init__(self):
        super().__init__(
            name="TranslationAgent",
            description="Translates document content while preserving formatting and style"
        )
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        text_content = input_data.get("text_content", "")
        document_analysis = input_data.get("document_analysis", {})
        target_language = input_data.get("target_language", "French")
        
        if not text_content:
            return {"error": "No text content provided"}
        
        # Create a specialized system prompt based on document analysis
        doc_type = document_analysis.get("document_type", "unknown")
        complexity = document_analysis.get("complexity_level", "medium")
        technical_terms = document_analysis.get("technical_terminology", [])
        
        # Build system prompt based on analysis
        system_prompt = f"""You are an expert translator specialized in {doc_type} documents with {complexity} 
        complexity. Translate accurately while preserving the original formatting, tone, and style. 
        Pay special attention to technical terminology."""
        
        # Add technical terms glossary if available
        technical_terms_str = ""
        if technical_terms:
            technical_terms_str = "Technical terms to preserve or handle with care:\n" + "\n".join(technical_terms)
        
        translation_prompt = f"""Please translate the following text from English to {target_language}. 
Maintain the original formatting, paragraphs, and style:

{technical_terms_str}

TEXT TO TRANSLATE:
{text_content}

Translation:"""
        
        translation = self.call_claude(
            prompt=translation_prompt,
            system=system_prompt,
            max_tokens=100000
        )
        
        return {
            "original_text": text_content,
            "translated_text": translation,
            "target_language": target_language
        }

# Contextual Enhancement Agent
class ContextualEnhancementAgent(BaseAgent):
    """Agent that improves translation by preserving tone, style, and adapting regional nuances"""
    
    def __init__(self):
        super().__init__(
            name="ContextualEnhancementAgent", 
            description="Enhances translations by adjusting tone, style, and dialect." 
        )
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        translated_text = input_data.get("translated_text", "")
        original_text = input_data.get("original_text", "")
        target_language = input_data.get("target_language", "French")
        
        if not translated_text:
            return {"error": "No translated text provided"}
        
        system_prompt = f"""You are an expert in language localization and translation refinement. Your task is to 
        improve the given translation while preserving tone, style, and adapting for {target_language} regional 
        dialects where applicable."""
        
        enhancement_prompt = f"""Enhance the following translation to better match the intended tone, style, and 
        regional nuances of {target_language}:
        
        ORIGINAL TEXT:
        {original_text}
        
        CURRENT TRANSLATION:
        {translated_text}
        
        Provide an improved translation that better preserves meaning, style, and tone.
        
        Improved Translation:"""
        
        enhanced_translation = self.call_claude(
            prompt=enhancement_prompt, 
            system=system_prompt, 
            max_tokens=100000
        )
        
        return {"enhanced_translation": enhanced_translation}

class QualityCheckAgent(BaseAgent):
    """Agent responsible for checking translation quality"""
    
    def __init__(self):
        super().__init__(
            name="QualityCheckAgent", 
            description="Verifies translation quality and makes corrections"
        )
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        original_text = input_data.get("original_text", "")
        translated_text = input_data.get("translated_text", "")
        target_language = input_data.get("target_language", "French")
        
        if not original_text or not translated_text:
            return {"error": "Missing original or translated text"}
        
        system_prompt = f"""You are an expert translation reviewer specialized in English to {target_language} 
        translations. Your task is to review the translation for accuracy, fluency, and preservation of 
        meaning and style."""
        
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
            
            review_prompt = f"""Review the quality of this translation from English to {target_language}.

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
2. Accuracy assessment (1-10)
3. Fluency assessment (1-10)
4. Style preservation assessment (1-10)
5. Specific issues found (if any)
6. Suggested corrections (if any)

Respond in JSON format.
"""
        else:
            review_prompt = f"""Review the quality of this translation from English to {target_language}.

ORIGINAL TEXT:
{original_text}

TRANSLATION:
{translated_text}

Please provide:
1. Overall quality assessment (1-10)
2. Accuracy assessment (1-10)
3. Fluency assessment (1-10)
4. Style preservation assessment (1-10)
5. Specific issues found (if any)
6. Suggested corrections (if any)

Respond in JSON format.
"""
        
        review_result = self.call_claude(review_prompt, system_prompt)
        
        # Try to extract JSON if present
        try:
            # Look for JSON pattern
            json_start = review_result.find('{')
            json_end = review_result.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = review_result[json_start:json_end]
                review_data = json.loads(json_str)
            else:
                review_data = {"review": review_result}
        except json.JSONDecodeError:
            review_data = {"review": review_result}
        
        # If quality is low, make corrections
        overall_quality = review_data.get("overall_quality", 0)
        if isinstance(overall_quality, str):
            try:
                overall_quality = int(overall_quality)
            except ValueError:
                overall_quality = 0
        
        final_translation = translated_text
        
        # If quality is below 7, try to improve the translation
        if overall_quality < 7 and "suggested_corrections" in review_data and review_data["suggested_corrections"]:
            correction_prompt = f"""Please correct the following translation based on these issues:

ORIGINAL TEXT:
{original_text}

CURRENT TRANSLATION:
{translated_text}

ISSUES IDENTIFIED:
{json.dumps(review_data.get("specific_issues", "No specific issues identified"))}

SUGGESTED CORRECTIONS:
{json.dumps(review_data.get("suggested_corrections", "No corrections suggested"))}

Please provide the improved translation:
"""
            
            improved_translation = self.call_claude(correction_prompt, system_prompt, max_tokens=100000)
            final_translation = improved_translation
        
        return {
            "original_text": original_text,
            "translated_text": final_translation,
            "quality_review": review_data,
            "target_language": target_language
        }


class TranslationWorkflow:
    """Orchestrates the entire translation process using agents"""
    
    def __init__(self):
        self.analysis_agent = DocumentAnalysisAgent()
        self.translation_agent = TranslationAgent()
        self.quality_agent = QualityCheckAgent()
        self.contextual_agent = ContextualEnhancementAgent()
    
    def process_document(self, text_content: str, target_language: str = "French") -> Dict[str, Any]:
        """Run the complete translation workflow"""
        
        # Step 1: Document analysis
        analysis_result = self.analysis_agent.process({
            "text_content": text_content
        })
        
        if "error" in analysis_result:
            return {"error": analysis_result["error"], "stage": "document_analysis"}
        
        # Step 2: Translation
        translation_result = self.translation_agent.process({
            "text_content": text_content,
            "document_analysis": analysis_result.get("document_analysis", {}),
            "target_language": target_language
        })
        
        if "error" in translation_result:
            return {"error": translation_result["error"], "stage": "translation"}
        
        # Step 3: Quality check
        quality_result = self.quality_agent.process({
            "original_text": text_content,
            "translated_text": translation_result.get("translated_text", ""),
            "target_language": target_language
        })
        
        if "error" in quality_result:
            return {"error": quality_result["error"], "stage": "quality_check"}
        
        # Step 4: Contextual enhancement
        enhanced_translation = self.contextual_agent.process({
            "original_text": text_content,
            "translated_text": quality_result.get("translated_text", ""),
            "target_language": target_language
        }).get("enhanced_translation", quality_result.get("translated_text", ""))
        
        # Return the final result
        return {
            "original_text": text_content,
            "translated_text": enhanced_translation,
            "document_analysis": analysis_result.get("document_analysis", {}),
            "quality_review": quality_result.get("quality_review", {}),
            "target_language": target_language
        }

# language-translation
Using agentic AI for language translation

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

# Integrating into Translation Workflow
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

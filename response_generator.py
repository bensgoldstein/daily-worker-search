"""Response generator using LLMs to enhance search results."""

import os
from typing import List, Optional
from loguru import logger

from models import SearchResult
from config import config


class ResponseGenerator:
    """Generate enhanced responses using LLMs."""
    
    def __init__(self):
        self.provider = config.LLM_PROVIDER
        self.model = None
        
        if self.provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=config.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(
                    config.LLM_MODEL,
                    generation_config={
                        "temperature": config.LLM_TEMPERATURE,
                        "max_output_tokens": config.LLM_MAX_TOKENS,
                    }
                )
                logger.info(f"Initialized Gemini model: {config.LLM_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                raise
                
        elif self.provider == "openai":
            try:
                import openai
                openai.api_key = config.OPENAI_API_KEY
                self.client = openai.OpenAI()
                logger.info(f"Initialized OpenAI model: {config.LLM_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                raise
    
    def generate_response(
        self,
        query: str,
        search_results: List[SearchResult],
        max_results_to_use: int = 5
    ) -> Optional[str]:
        """Generate an enhanced response based on search results."""
        
        if not self.model and self.provider != "openai":
            return None
        
        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(search_results[:max_results_to_use]):
            citation = result.format_citation()
            context_parts.append(
                f"[Source {i+1}] {citation}\n"
                f"Content: {result.chunk.content}\n"
            )
        
        context = "\n---\n".join(context_parts)
        
        # Create prompt
        prompt = self._create_prompt(query, context)
        
        try:
            if self.provider == "gemini":
                response = self.model.generate_content(prompt)
                return response.text
                
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=config.LLM_MAX_TOKENS
                )
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are a helpful historical research assistant specializing in newspaper archives. 
Your role is to synthesize information from historical newspaper articles to answer questions accurately.
Always cite your sources using the provided source numbers.
Focus on factual information and historical context.
If information is unclear or contradictory between sources, acknowledge this."""
    
    def _create_prompt(self, query: str, context: str) -> str:
        """Create the prompt for the LLM."""
        return f"""Based on the following historical newspaper articles, please answer this question: {query}

Historical Sources:
{context}

Please provide a comprehensive answer that:
1. Directly addresses the question
2. Synthesizes information from multiple sources
3. Includes specific dates, names, and events mentioned
4. Cites sources using [Source N] format
5. Provides historical context when relevant

If the sources don't contain enough information to fully answer the question, acknowledge this and explain what information is available."""
    
    def format_response_with_citations(
        self,
        response: str,
        search_results: List[SearchResult]
    ) -> str:
        """Format the response with proper citations at the end."""
        
        if not response:
            return ""
        
        # Add citations section
        citations = ["\n\n### Sources Referenced:"]
        for i, result in enumerate(search_results[:5]):
            citation = result.format_citation()
            citations.append(f"[Source {i+1}] {citation}")
        
        return response + "\n".join(citations)
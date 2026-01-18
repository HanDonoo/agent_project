"""
LLM Integration for AI Agent
Supports OpenAI API and OpenAI-compatible endpoints (like OpenWebUI's backend)
"""
import os
import json
from typing import List, Dict, Optional, Any
import requests
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Generate response from LLM"""
        pass


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider
    Also works with OpenAI-compatible endpoints (Ollama, LocalAI, etc.)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.temperature = temperature
    
    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Generate response using OpenAI API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling
            
        Returns:
            Response dict with 'content' and optional 'tool_calls'
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            choice = result['choices'][0]
            message = choice['message']
            
            return {
                'content': message.get('content', ''),
                'tool_calls': message.get('tool_calls', []),
                'finish_reason': choice.get('finish_reason', 'stop')
            }
            
        except Exception as e:
            # Fallback to non-AI response
            return {
                'content': f"Error calling LLM: {str(e)}",
                'tool_calls': [],
                'finish_reason': 'error'
            }


class LocalLLMProvider(LLMProvider):
    """
    Local LLM provider (for Ollama, LocalAI, etc.)
    Uses OpenAI-compatible API format
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",  # Ollama default
        model: str = "llama2",
        temperature: float = 0.7
    ):
        self.openai_provider = OpenAIProvider(
            api_key="not-needed",  # Local models don't need API key
            base_url=base_url,
            model=model,
            temperature=temperature
        )
    
    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Generate response using local LLM"""
        return self.openai_provider.generate(messages, tools)


class LLMManager:
    """
    Manages LLM interactions for the agent
    Handles provider selection and fallback
    """
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> LLMProvider:
        """Get default LLM provider based on environment"""
        # Check for OpenAI API key
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider()
        
        # Check for local LLM endpoint
        local_endpoint = os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:11434/v1")
        local_model = os.getenv("LOCAL_LLM_MODEL", "llama2")
        
        return LocalLLMProvider(base_url=local_endpoint, model=local_model)
    
    def understand_query(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Use LLM to understand user query and extract intent
        
        Args:
            user_query: User's natural language query
            context: Optional context (previous conversation, etc.)
            
        Returns:
            Dict with extracted intent, entities, and suggested actions
        """
        system_prompt = """You are an AI assistant helping employees find the right people in their organization.

Your task is to understand the user's query and extract:
1. What they need help with (domain/responsibility)
2. Any specific requirements (team, location, skills)
3. The type of search needed

Respond in JSON format:
{
    "intent": "brief description of what user needs",
    "domains": ["list", "of", "relevant", "domains"],
    "requirements": {
        "team": "team name if mentioned",
        "location": "location if mentioned",
        "skills": ["required", "skills"]
    },
    "search_strategy": "responsibility" | "skill" | "team" | "fulltext"
}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        response = self.provider.generate(messages)
        
        try:
            # Try to parse JSON from response
            content = response['content']
            # Extract JSON from markdown code blocks if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            parsed = json.loads(content)
            return parsed
        except:
            # Fallback to simple parsing
            return {
                "intent": user_query,
                "domains": [],
                "requirements": {},
                "search_strategy": "fulltext"
            }


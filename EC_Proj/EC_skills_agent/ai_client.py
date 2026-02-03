"""
Unified AI Client for both Ollama and Gemini
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import requests
import logging

logger = logging.getLogger(__name__)


class AIClient(ABC):
    """Abstract base class for AI clients"""
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, timeout: int = 300) -> str:
        """
        Send chat messages and get response
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            timeout: Request timeout in seconds
            
        Returns:
            Response content as string
        """
        pass


class OllamaClient(AIClient):
    """Ollama local model client"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        logger.info(f"🤖 Initialized Ollama client: {base_url}, model: {model}")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, timeout: int = 300) -> str:
        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=timeout,
            )
            r.raise_for_status()
            data = r.json()
            return data["message"]["content"]
        except Exception as e:
            logger.error(f"❌ Ollama error: {e}")
            raise


class GeminiClient(AIClient):
    """Google Gemini API client"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1"
        logger.info(f"🌟 Initialized Gemini client: model: {model}")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, timeout: int = 300) -> str:
        """
        Send chat request to Gemini API
        
        Gemini uses a different message format:
        - Ollama: [{"role": "user", "content": "..."}]
        - Gemini: {"contents": [{"parts": [{"text": "..."}], "role": "user"}]}
        """
        try:
            # Convert Ollama format to Gemini format
            gemini_contents = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]

                # Gemini uses "user" and "model" instead of "user" and "assistant"
                if role == "assistant":
                    role = "model"
                # Gemini doesn't support "system" role - convert to user message
                elif role == "system":
                    role = "user"
                    # Prepend system instruction to make it clear
                    content = f"[SYSTEM INSTRUCTION] {content}"

                gemini_contents.append({
                    "parts": [{"text": content}],
                    "role": role
                })
            
            # Prepare request
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            
            payload = {
                "contents": gemini_contents,
                "generationConfig": {
                    "temperature": temperature,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                }
            }
            
            logger.debug(f"📤 Sending request to Gemini: {self.model}")
            
            r = requests.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            
            data = r.json()
            
            # Extract response text
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        response_text = parts[0]["text"]
                        logger.debug(f"✅ Received response from Gemini ({len(response_text)} chars)")
                        return response_text
            
            # If we get here, the response format was unexpected
            logger.error(f"❌ Unexpected Gemini response format: {data}")
            raise RuntimeError(f"Unexpected Gemini response format: {data}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Gemini API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"   Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Gemini error: {e}")
            raise

    def list_models(self, timeout: int = 30) -> dict:
        url = f"{self.base_url}/models?key={self.api_key}"
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()



def create_ai_client(provider: str, **kwargs) -> AIClient:
    """
    Factory function to create AI client based on provider
    
    Args:
        provider: "ollama" or "gemini"
        **kwargs: Provider-specific arguments
            For Ollama: base_url, model
            For Gemini: api_key, model
    
    Returns:
        AIClient instance
    """
    if provider == "ollama":
        return OllamaClient(
            base_url=kwargs.get("base_url", "http://localhost:11434"),
            model=kwargs.get("model", "llama3.2:3b")
        )
    elif provider == "gemini":
        
        return GeminiClient(
            api_key=kwargs.get("api_key", ""),
            model=kwargs.get("model", "gemini-1.5-flash")
        )
    else:
        raise ValueError(f"Unknown AI provider: {provider}. Must be 'ollama' or 'gemini'")


"""
LLM Client - Provider-agnostic interface for LLM calls.
Supports Anthropic, OpenAI, Gemini, and Groq through environment variables.
"""

import os
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def generate_json(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Generate a JSON response from the LLM."""
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""
    
    def __init__(self, api_key: str, model: str):
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
        """Generate a text response."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return message.content[0].text
    
    def generate_json(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Generate a JSON response."""
        json_instruction = "\n\nRespond with valid JSON only, no other text."
        response = self.generate(system_prompt + json_instruction, user_message, temperature)
        
        # Try to extract JSON from the response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise ValueError(f"Failed to parse JSON from LLM response: {response}")


class OpenAIClient(LLMClient):
    """OpenAI GPT client."""
    
    def __init__(self, api_key: str, model: str):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
        """Generate a text response."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    
    def generate_json(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Generate a JSON response."""
        json_instruction = "\n\nRespond with valid JSON only, no other text."
        response = self.generate(system_prompt + json_instruction, user_message, temperature)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise ValueError(f"Failed to parse JSON from LLM response: {response}")


class GeminiClient(LLMClient):
    """Google Gemini client."""
    
    def __init__(self, api_key: str, model: str):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
        """Generate a text response."""
        full_prompt = f"{system_prompt}\n\nUser: {user_message}"
        response = self.model.generate_content(
            full_prompt,
            generation_config={"temperature": temperature}
        )
        return response.text
    
    def generate_json(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Generate a JSON response."""
        json_instruction = "\n\nRespond with valid JSON only, no other text."
        response = self.generate(system_prompt + json_instruction, user_message, temperature)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise ValueError(f"Failed to parse JSON from LLM response: {response}")


class GroqClient(LLMClient):
    """Groq client (uses OpenAI-compatible API)."""
    
    def __init__(self, api_key: str, model: str):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        # Groq uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = model
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
        """Generate a text response."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    
    def generate_json(self, system_prompt: str, user_message: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Generate a JSON response."""
        json_instruction = "\n\nRespond with valid JSON only, no other text."
        response = self.generate(system_prompt + json_instruction, user_message, temperature)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise ValueError(f"Failed to parse JSON from LLM response: {response}")


def create_llm_client(provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None) -> LLMClient:
    """
    Factory function to create an LLM client based on environment variables or parameters.
    
    Args:
        provider: LLM provider ('anthropic', 'openai', 'gemini', 'groq'). Defaults to env var LLM_PROVIDER.
        api_key: API key for the provider. Defaults to env var LLM_API_KEY.
        model: Model name. Defaults to env var LLM_MODEL or provider default.
    
    Returns:
        LLMClient instance
    """
    provider = provider or os.getenv("LLM_PROVIDER", "anthropic").lower()
    api_key = api_key or os.getenv("LLM_API_KEY")
    
    if not api_key:
        raise ValueError("LLM_API_KEY environment variable not set")
    
    # Set default models if not specified
    default_models = {
        "anthropic": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o",
        "gemini": "gemini-pro",
        "groq": "llama-3.3-70b-versatile"  # Best Groq model for general tasks
    }
    
    model = model or os.getenv("LLM_MODEL") or default_models.get(provider)
    
    if provider == "anthropic":
        return AnthropicClient(api_key, model)
    elif provider == "openai":
        return OpenAIClient(api_key, model)
    elif provider == "gemini":
        return GeminiClient(api_key, model)
    elif provider == "groq":
        return GroqClient(api_key, model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

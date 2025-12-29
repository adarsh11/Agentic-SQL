"""
LLM Client for Multi-Agent SQL System
Primary: Groq API with Moonshot model
Fallback: Mistral AI API with Mistral Small
"""

import os
import json
from openai import OpenAI
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Singleton LLM client with fallback support"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize primary and fallback clients"""
        # Primary: Groq/Moonshot
        self.primary_api_key = os.getenv("GROQ_API_KEY")
        self.primary_base_url = "https://api.groq.com/openai/v1"
        self.primary_model = "moonshotai/kimi-k2-instruct-0905" #"llama-3.3-70b-versatile"
        
        if self.primary_api_key:
            self.primary_client = OpenAI(api_key=self.primary_api_key, base_url=self.primary_base_url)
        else:
            self.primary_client = None
            print("Warning: GROQ_API_KEY not set. Primary model will be skipped.")

        # Fallback: Mistral
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.mistral_model = "mistral-small-latest"
        
        if not self.mistral_api_key:
            print("Warning: MISTRAL_API_KEY not set. Fallback model will be unavailable.")

    def generate(
        self, 
        prompt: str, 
        system_prompt: str = "You are a helpful AI assistant.", 
        temperature: float = 0.5, 
        max_tokens: int = 1000
    ) -> str:
        """Generate text with primary model and fallback to Mistral if primary fails"""
        # Try Primary
        if self.primary_client:
            try:
                response = self.primary_client.chat.completions.create(
                    model=self.primary_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Primary LLM generation error: {e}. Falling back to Mistral...")

        # Fallback to Mistral
        if self.mistral_api_key:
            try:
                with Mistral(api_key=self.mistral_api_key) as mistral:
                    res = mistral.chat.complete(
                        model=self.mistral_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    return res.choices[0].message.content
            except Exception as e:
                print(f"Fallback Mistral generation error: {e}")
                raise
        
        raise ValueError("Both primary and fallback LLM models failed or are not configured.")

    def generate_with_tools(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant.",
        tools: list = None,
        tool_choice: str = "auto",
        temperature: float = 0.5,
        max_tokens: int = 1000
    ) -> dict:
        """Generate response with tool calling and fallback"""
        # Try Primary
        if self.primary_client:
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
                params = {
                    "model": self.primary_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if tools:
                    params["tools"] = tools
                    params["tool_choice"] = tool_choice
                
                response = self.primary_client.chat.completions.create(**params)
                message = response.choices[0].message
                
                result = {"content": message.content, "tool_calls": []}
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    result["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                return result
            except Exception as e:
                print(f"Primary tool call error: {e}. Falling back to Mistral...")

        # Fallback to Mistral
        if self.mistral_api_key:
            try:
                with Mistral(api_key=self.mistral_api_key) as mistral:
                    # Convert OpenAI tool format to Mistral if necessary
                    # Mistral SDK expects similar format but let's be careful
                    params = {
                        "model": self.mistral_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    if tools:
                        params["tools"] = tools
                        params["tool_choice"] = tool_choice
                    
                    res = mistral.chat.complete(**params)
                    message = res.choices[0].message
                    
                    result = {"content": message.content, "tool_calls": []}
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        result["tool_calls"] = [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    return result
            except Exception as e:
                print(f"Fallback Mistral tool call error: {e}")
                raise

        raise ValueError("Both primary and fallback LLM models failed or are not configured.")

    def chat(
        self,
        messages: list,
        temperature: float = 0.5,
        max_tokens: int = 1000,
        tools: list = None,
        tool_choice: str = "auto"
    ) -> dict:
        """Chat with fallback"""
        # Try Primary
        if self.primary_client:
            try:
                params = {
                    "model": self.primary_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if tools:
                    params["tools"] = tools
                    params["tool_choice"] = tool_choice
                
                response = self.primary_client.chat.completions.create(**params)
                message = response.choices[0].message
                
                result = {"content": message.content, "tool_calls": [], "role": message.role}
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    result["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                return result
            except Exception as e:
                print(f"Primary chat error: {e}. Falling back to Mistral...")

        # Fallback to Mistral
        if self.mistral_api_key:
            try:
                with Mistral(api_key=self.mistral_api_key) as mistral:
                    params = {
                        "model": self.mistral_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    if tools:
                        params["tools"] = tools
                        params["tool_choice"] = tool_choice
                    
                    res = mistral.chat.complete(**params)
                    message = res.choices[0].message
                    
                    result = {"content": message.content, "tool_calls": [], "role": message.role}
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        result["tool_calls"] = [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    return result
            except Exception as e:
                print(f"Fallback Mistral chat error: {e}")
                raise

        raise ValueError("Both primary and fallback LLM models failed or are not configured.")


# Singleton instance
def get_llm_client() -> LLMClient:
    """Get the singleton LLM client instance"""
    return LLMClient()

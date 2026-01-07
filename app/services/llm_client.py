"""
LLM client wrapper for unified access to different LLM providers.
Supports OpenAI, Google Gemini, and local models via Ollama.
"""
from typing import Optional, Dict, Any
import json

from app.core.config import settings
from app.core.logging_config import logger

# Import requests for Ollama health check
try:
    import requests
except ImportError:
    requests = None  # Will be handled gracefully


class LLMClient:
    """Unified LLM client supporting multiple providers."""
    
    def __init__(self, provider: str = None, model: str = None):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (openai, gemini, ollama)
            model: Model name
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        
        logger.info(f"Initializing LLM client: {self.provider}/{self.model}")
        
        # Initialize provider-specific client
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "ollama":
            self._init_ollama()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.LLM_TIMEOUT
            )
            logger.info(f"OpenAI client initialized with {settings.LLM_TIMEOUT}s timeout")
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def _init_gemini(self):
        """Initialize Google Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.client = genai.GenerativeModel(self.model)
            logger.info("Gemini client initialized")
        except ImportError:
            raise ImportError("Google GenAI package not installed. Run: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def _init_ollama(self):
        """Initialize Ollama client for remote connection."""
        try:
            from openai import OpenAI
            
            # Check if remote Ollama is accessible (if requests is available)
            if requests:
                try:
                    health_url = settings.OLLAMA_BASE_URL.replace('/v1', '')
                    response = requests.get(f"{health_url}/api/tags", timeout=10)
                    if response.status_code != 200:
                        logger.warning(f"Remote Ollama health check returned status {response.status_code}")
                    else:
                        logger.info("Remote Ollama connection verified")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Could not connect to remote Ollama at {health_url}: {e}")
                    logger.warning("Proceeding with configuration - connection will be tested during generation")
            
            # Remote Ollama uses OpenAI-compatible API with extended timeout
            self.client = OpenAI(
                base_url=settings.OLLAMA_BASE_URL,
                api_key="ollama",  # Remote Ollama doesn't require real API key
                timeout=settings.LLM_TIMEOUT
            )
            logger.info(f"Remote Ollama client initialized with {settings.LLM_TIMEOUT}s timeout")
            logger.info(f"Target model: {settings.LLM_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize remote Ollama client: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False
    ) -> str:
        """
        Generate text using the LLM.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            json_mode: Whether to request JSON output
        
        Returns:
            Generated text
        """
        temperature = temperature or settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        
        logger.debug(f"Generating with {self.provider}: temp={temperature}, max_tokens={max_tokens}")
        
        try:
            if self.provider == "openai" or self.provider == "ollama":
                return self._generate_openai(prompt, temperature, max_tokens, json_mode)
            elif self.provider == "gemini":
                return self._generate_gemini(prompt, temperature, max_tokens)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def _generate_openai(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> str:
        """Generate using OpenAI API."""
        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    def _generate_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Google Gemini API."""
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens
        }
        
        response = self.client.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.
        
        Args:
            response: LLM response text
        
        Returns:
            Parsed JSON dict
        """
        try:
            # Try direct JSON parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                logger.error(f"Failed to parse JSON from response: {response[:200]}")
                raise ValueError("Could not parse JSON from LLM response")

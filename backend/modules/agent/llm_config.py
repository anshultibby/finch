"""
LLM Configuration - Type-safe settings for LiteLLM calls
"""
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """
    Configuration for LLM API calls via LiteLLM
    
    Provides type-safe defaults and validation for all LiteLLM parameters.
    """
    
    # Model selection
    model: str = Field(description="Model to use (e.g., 'gpt-5', 'gpt-4o')")
    
    # API keys
    api_key: Optional[str] = Field(None, description="API key for the provider")
    
    # Core parameters
    temperature: float = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    
    # Streaming
    stream: bool = Field(False, description="Enable streaming responses")
    stream_options: Optional[Dict[str, Any]] = Field(None, description="Streaming options")
    
    # OpenAI-specific
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = Field(
        None, 
        description="Reasoning effort for o1/o3 models"
    )
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    
    # Performance
    caching: bool = Field(False, description="Enable prompt caching (if supported)")
    timeout: Optional[float] = Field(None, gt=0, description="Request timeout in seconds")
    
    # Other
    stop: Optional[list[str]] = Field(None, description="Stop sequences")
    user: Optional[str] = Field(None, description="User identifier for tracking")
    
    class Config:
        validate_assignment = True
        extra = "allow"  # Allow additional provider-specific params
    
    def to_litellm_kwargs(self) -> Dict[str, Any]:
        """
        Convert to LiteLLM kwargs dictionary
        
        Returns:
            Dict with only non-None values for passing to acompletion()
        """
        kwargs = {}
        
        # Always include model
        kwargs["model"] = self.model
        
        # Add all non-None values
        for field_name, value in self.dict(exclude={"model"}).items():
            if value is not None:
                kwargs[field_name] = value
        
        return kwargs
    
    @staticmethod
    def _get_model_defaults(model: str) -> Dict[str, Any]:
        """
        Get model-specific defaults based on model name prefix
        
        Args:
            model: Model name (e.g., "gpt-5", "gpt-4o", "claude-3-5-sonnet")
        
        Returns:
            Dict of default parameters for that model family
        """
        model_lower = model.lower()
        
        # OpenAI o1/o3 series (reasoning models)
        if model_lower.startswith(("gpt-5", "o1", "o3")):
            return {
                "reasoning_effort": "medium",
                "caching": True,
                "seed": 42,
            }
        
        # OpenAI GPT-4o series
        elif model_lower.startswith("gpt-4o"):
            return {
                "caching": True,
                "seed": 42,
            }
        
        # OpenAI GPT-4 series
        elif model_lower.startswith("gpt-4"):
            return {
                "caching": True,
                "seed": 42,
            }
        
        # Anthropic Claude (handles both "claude-..." and "anthropic/claude-...")
        elif model_lower.startswith("claude") or model_lower.startswith("anthropic/"):
            return {
                "caching": True,
                "max_tokens": 16000,  # Higher limit for file writes - Claude default is only 4096
            }
        
        # Google Gemini
        elif model_lower.startswith("gemini"):
            return {
                "caching": False,  # Gemini handles caching differently
            }
        
        # Default fallback
        else:
            return {
                "caching": True,
                "seed": 42,
            }
    
    @staticmethod
    def _get_api_key_for_model(model: str) -> Optional[str]:
        """
        Get the appropriate API key based on model provider
        
        Args:
            model: Model name (e.g., "gpt-5", "claude-sonnet-4-20250514", "gemini/gemini-2.5-pro")
        
        Returns:
            API key for the model's provider
        """
        from config import Config
        
        model_lower = model.lower()
        
        # Anthropic Claude models (handles both "claude-..." and "anthropic/claude-...")
        if model_lower.startswith("claude") or model_lower.startswith("anthropic/"):
            return Config.ANTHROPIC_API_KEY
        
        # Google Gemini models (both "gemini/" prefix and direct "gemini-" names)
        if model_lower.startswith("gemini"):
            return Config.GEMINI_API_KEY
        
        # OpenAI models (default)
        return Config.OPENAI_API_KEY
    
    @staticmethod
    def from_config(
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 1.0,
        **overrides
    ) -> "LLMConfig":
        """
        Create LLMConfig with smart defaults based on model family
        
        Auto-detects model-specific settings (e.g., reasoning_effort for o1/o3 models).
        
        Args:
            model: Model name (default: from Config.LLM_MODEL)
            stream: Enable streaming (default: False)
            temperature: Sampling temperature (default: 1.0)
            **overrides: Override any LLMConfig field
        
        Examples:
            # Use default model from config
            LLMConfig.from_config(stream=True)
            
            # Specify model (auto-detects o1 defaults)
            LLMConfig.from_config(model="gpt-5", stream=True)
            
            # Use Claude 4.5 Sonnet
            LLMConfig.from_config(model="claude-sonnet-4-5-20250929", stream=True)
            
            # Override specific fields
            LLMConfig.from_config(
                model="gpt-4o",
                stream=True,
                temperature=0.5,
                max_tokens=2000
            )
        """
        from config import Config
        
        # Determine model (default to PLANNER_LLM_MODEL if not specified)
        selected_model = model or Config.PLANNER_LLM_MODEL
        
        # Get model-specific defaults
        model_defaults = LLMConfig._get_model_defaults(selected_model)
        
        # Get the correct API key for this model
        api_key = LLMConfig._get_api_key_for_model(selected_model)
        
        # Base config
        defaults = {
            "model": selected_model,
            "api_key": api_key,
            "temperature": temperature,
            "stream": stream,
            "stream_options": {"include_usage": False} if stream else None,
        }
        
        # Merge in model-specific defaults
        defaults.update(model_defaults)
        
        # Apply user overrides (highest priority)
        defaults.update(overrides)
        
        return LLMConfig(**defaults)


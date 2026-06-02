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
    
    # Reasoning / extended thinking
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = Field(
        None,
        description="Reasoning effort for OpenAI reasoning models (gpt-5/o1/o3)"
    )
    thinking: Optional[Dict[str, Any]] = Field(
        None,
        description="Anthropic extended-thinking config, e.g. {'type':'enabled','budget_tokens':10000}"
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

        # Add all non-None values (exclude internal flags not passed to litellm)
        for field_name, value in self.dict(exclude={"model", "caching"}).items():
            if value is not None:
                kwargs[field_name] = value

        # Defensive guard: Anthropic requires budget_tokens < max_tokens. If a caller
        # set a small max_tokens (e.g. a short utility call), drop thinking rather than
        # let the API reject the request.
        thinking = kwargs.get("thinking")
        if isinstance(thinking, dict) and thinking.get("type") == "enabled":
            budget = thinking.get("budget_tokens", 0)
            max_tokens = kwargs.get("max_tokens")
            if not max_tokens or budget >= max_tokens:
                kwargs.pop("thinking", None)

        return kwargs
    
    @staticmethod
    def _get_model_defaults(model: str) -> Dict[str, Any]:
        """
        Get model-specific defaults from the central model registry.

        See `core.model_registry` to add or tune a model family.
        """
        from core.model_registry import get_defaults
        return get_defaults(model)

    @staticmethod
    def _get_api_key_for_model(model: str) -> Optional[str]:
        """
        Get the appropriate API key for `model`'s provider from the registry.

        See `core.model_registry` to add or tune a model family.
        """
        from core.model_registry import get_api_key
        return get_api_key(model)

    @staticmethod
    def from_config(
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 1.0,
        reasoning_effort: Optional[str] = None,
        **overrides
    ) -> "LLMConfig":
        """
        Create LLMConfig with smart defaults based on model family.

        All provider-specific behaviour (defaults, API key, reasoning/thinking) is
        resolved through `core.model_registry`.

        Args:
            model: Model name (default: Config.AGENT_LLM_MODEL)
            stream: Enable streaming (default: False)
            temperature: Sampling temperature (default: 1.0; must be 1.0 for Claude
                thinking, which is the default)
            reasoning_effort: "low" | "medium" | "high". Overrides the model's default
                thinking budget / reasoning effort. None uses the family default.
            **overrides: Override any LLMConfig field (highest priority)

        Examples:
            LLMConfig.from_config(stream=True)                       # default model
            LLMConfig.from_config(model="zai/glm-5.1", stream=True)  # GLM
            LLMConfig.from_config(model="anthropic/claude-sonnet-4-6",
                                  reasoning_effort="high")           # bigger thinking budget
        """
        from core.config import Config
        from core.model_registry import reasoning_params

        # Determine model (default to AGENT_LLM_MODEL if not specified)
        selected_model = model or Config.AGENT_LLM_MODEL

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

        # Merge in reasoning/thinking params (scales max_tokens with the thinking
        # budget for Anthropic). Applied after defaults so it can raise max_tokens.
        defaults.update(reasoning_params(selected_model, reasoning_effort))

        # Apply user overrides (highest priority)
        defaults.update(overrides)

        return LLMConfig(**defaults)


"""
Standard tool response models - enforced by decorator

All tools must return a ToolResponse or one of its subclasses.
"""
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class ToolResponse(BaseModel):
    """
    Standard response format for all tools.
    
    Tools MUST return this format (enforced by decorator).
    
    Example:
        return ToolResponse(
            success=True,
            data={"portfolio": [...]}
        )
    """
    success: bool = Field(description="Whether the tool executed successfully")
    data: Any = Field(default=None, description="Tool result data")
    message: Optional[str] = Field(default=None, description="Human-readable message for LLM")
    error: Optional[str] = Field(default=None, description="Error message if success=False")
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_llm_content(self) -> str:
        """
        Convert to content string for LLM conversation.
        
        Tools can override this method for custom formatting.
        By default, returns JSON representation.
        """
        import json
        return json.dumps(self.model_dump(), indent=2)


class ToolSuccess(ToolResponse):
    """Convenience class for successful tool responses"""
    success: bool = Field(default=True, frozen=True)
    
    def __init__(self, data: Any = None, message: Optional[str] = None, **kwargs):
        super().__init__(success=True, data=data, message=message, error=None, **kwargs)


class ToolError(ToolResponse):
    """Convenience class for error responses"""
    success: bool = Field(default=False, frozen=True)
    
    def __init__(self, error: str, message: Optional[str] = None, data: Any = None, **kwargs):
        super().__init__(success=False, error=error, message=message, data=data, **kwargs)


# Example specialized responses

class PortfolioResponse(ToolSuccess):
    """Specialized response for portfolio tools"""
    data: Dict[str, Any] = Field(description="Portfolio data with positions")
    
    def to_llm_content(self) -> str:
        """Custom formatting for portfolio data"""
        import json
        portfolio = self.data
        
        # Create a human-readable summary
        summary = {
            "success": True,
            "portfolio": portfolio,
            "summary": self.message or "Portfolio retrieved successfully"
        }
        
        return json.dumps(summary, indent=2)


class ChartResponse(ToolSuccess):
    """Specialized response for chart/visualization tools"""
    data: Dict[str, Any] = Field(description="Chart configuration and data")
    
    def to_llm_content(self) -> str:
        """Custom formatting for chart data"""
        import json
        return json.dumps({
            "success": True,
            "chart_created": True,
            "chart_id": self.data.get("resource_id"),
            "title": self.data.get("title"),
            "type": self.data.get("type"),
            "message": self.message or "Chart created successfully"
        }, indent=2)


class DataResponse(ToolSuccess):
    """Specialized response for data fetching tools"""
    
    def to_llm_content(self) -> str:
        """Custom formatting that handles large datasets"""
        import json
        
        data = self.data
        
        # If data is a list and large, provide summary
        if isinstance(data, list) and len(data) > 10:
            summary = {
                "success": True,
                "record_count": len(data),
                "sample": data[:5],  # First 5 records
                "message": self.message or f"Retrieved {len(data)} records"
            }
            return json.dumps(summary, indent=2)
        
        # Otherwise return full data
        return super().to_llm_content()


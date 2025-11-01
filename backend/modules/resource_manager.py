"""
Resource Manager for handling resources in the chat system

Resources are data artifacts created by tools (plots, tables, etc.) that can be:
1. Visible to the model via system prompt
2. Referenced by ID in subsequent tool calls
3. Loaded from database (DB is the source of truth)

Tools write directly to DB using resource_crud.
ResourceManager provides read-only access and system prompt generation.
"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from datetime import datetime

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ResourceReference(BaseModel):
    """
    A lightweight reference to a resource (for system prompt)
    """
    id: str = Field(description="Unique resource ID")
    tool_name: str = Field(description="Name of tool that created this resource")
    resource_type: str = Field(description="Type of resource (plot, table, portfolio, etc.)")
    title: str = Field(description="Human-readable title")
    created_at: str = Field(description="Creation timestamp")
    data_summary: Optional[str] = Field(None, description="Brief summary of data (e.g., '50 items')")
    
    def to_system_description(self) -> str:
        """
        Generate a description of this resource for the system prompt
        
        Returns a concise description that helps the model understand what resources
        are available and how to reference them.
        """
        desc = f"- **{self.title}** (ID: `{self.id}`, Type: {self.resource_type})"
        
        # Add contextual information based on resource type
        if self.resource_type == "plot":
            desc += " - Interactive chart/visualization"
        elif self.resource_type == "portfolio":
            desc += " - Portfolio holdings data"
        elif self.resource_type in ["senate_trades", "house_trades", "insider_trades"]:
            desc += " - Trading activity data"
        elif self.resource_type in ["reddit_trends", "reddit_sentiment"]:
            desc += " - Reddit sentiment/trending data"
        
        # Add data summary if available
        if self.data_summary:
            desc += f" ({self.data_summary})"
        
        return desc


class ResourceManager:
    """
    Manages resources for a chat session (READ-ONLY)
    
    Resources are:
    - Loaded from database when needed
    - Created by tools writing directly to DB via resource_crud
    - Referenced by ID in subsequent tool calls
    - Included in system prompts for model visibility
    
    This is a lightweight read-only wrapper around the database.
    """
    
    def __init__(self, chat_id: str, user_id: str, db: Optional[Any] = None):
        """
        Initialize resource manager
        
        Args:
            chat_id: Chat session ID
            user_id: User ID
            db: Optional database session for querying resources
        """
        self.chat_id = chat_id
        self.user_id = user_id
        self._db = db
        self._cached_resources: Dict[str, ResourceReference] = {}
    
    def load_resources(self, db: Optional[Any] = None, limit: int = 50):
        """
        Load resources from database for this chat
        
        Args:
            db: Database session (uses stored session if not provided)
            limit: Maximum number of resources to load
        """
        from crud import resource as resource_crud
        
        db_session = db or self._db
        if not db_session:
            print("⚠️ No database session available for loading resources", flush=True)
            return
        
        # Load resources from DB
        db_resources = resource_crud.get_chat_resources(db_session, self.chat_id, limit=limit)
        
        # Convert to ResourceReference objects
        self._cached_resources.clear()
        for db_resource in db_resources:
            # Calculate data summary
            data_summary = None
            if isinstance(db_resource.data, dict):
                if "data" in db_resource.data and isinstance(db_resource.data["data"], list):
                    data_summary = f"{len(db_resource.data['data'])} items"
            
            ref = ResourceReference(
                id=db_resource.id,
                tool_name=db_resource.tool_name,
                resource_type=db_resource.resource_type,
                title=db_resource.title,
                created_at=db_resource.created_at.isoformat(),
                data_summary=data_summary
            )
            self._cached_resources[ref.id] = ref
        
        print(f"📚 Loaded {len(self._cached_resources)} resources for chat {self.chat_id}", flush=True)
    
    def get_resource(self, resource_id: str, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """
        Get a resource's full data by ID from database
        
        Args:
            resource_id: Resource ID
            db: Database session
        
        Returns:
            Resource data dict or None if not found
        """
        from crud import resource as resource_crud
        
        db_session = db or self._db
        if not db_session:
            print(f"⚠️ No database session available for getting resource {resource_id}", flush=True)
            return None
        
        db_resource = resource_crud.get_resource(db_session, resource_id)
        if not db_resource:
            return None
        
        return {
            "id": db_resource.id,
            "tool_name": db_resource.tool_name,
            "resource_type": db_resource.resource_type,
            "title": db_resource.title,
            "data": db_resource.data,
            "metadata": db_resource.resource_metadata,
            "created_at": db_resource.created_at.isoformat()
        }
    
    def get_resources_by_type(self, resource_type: str) -> List[ResourceReference]:
        """
        Get all cached resources of a specific type
        
        Args:
            resource_type: Type of resource to filter by
        
        Returns:
            List of matching resource references
        """
        return [r for r in self._cached_resources.values() if r.resource_type == resource_type]
    
    def list_resources(self) -> List[ResourceReference]:
        """
        Get all cached resources
        
        Returns:
            List of all resource references
        """
        return list(self._cached_resources.values())
    
    def to_system_prompt_section(self) -> str:
        """
        Generate a system prompt section describing available resources
        
        This makes resources visible to the model so it can:
        1. Know what data is available
        2. Reference resources by ID in tool calls
        3. Avoid redundant data fetching
        
        Returns:
            Formatted string for inclusion in system prompt
        """
        if not self._cached_resources:
            return ""
        
        # Group resources by type for better organization
        by_type: Dict[str, List[ResourceReference]] = {}
        for resource in self._cached_resources.values():
            if resource.resource_type not in by_type:
                by_type[resource.resource_type] = []
            by_type[resource.resource_type].append(resource)
        
        # Build prompt section
        lines = ["\n## Available Resources"]
        lines.append("The following resources are available in this conversation. You can reference them by ID in tool calls like plot_from_resource:")
        lines.append("")
        
        # Group by category
        categories = {
            "Charts & Visualizations": ["plot"],
            "Portfolio Data": ["portfolio"],
            "Trading Activity": ["senate_trades", "house_trades", "insider_trades", "ticker_insider_activity"],
            "Market Sentiment": ["reddit_trends", "reddit_sentiment", "reddit_comparison"],
            "Other": []
        }
        
        for category, types in categories.items():
            category_resources = []
            for rtype in types:
                if rtype in by_type:
                    category_resources.extend(by_type[rtype])
            
            if category_resources:
                lines.append(f"### {category}")
                for resource in sorted(category_resources, key=lambda r: r.created_at, reverse=True):
                    lines.append(resource.to_system_description())
                lines.append("")
        
        # Add any uncategorized resources
        categorized_types = [t for types in categories.values() for t in types]
        other_resources = [r for r in self._cached_resources.values() if r.resource_type not in categorized_types]
        if other_resources:
            lines.append("### Other")
            for resource in sorted(other_resources, key=lambda r: r.created_at, reverse=True):
                lines.append(resource.to_system_description())
            lines.append("")
        
        return "\n".join(lines)


"""
Resource Manager - File system for chat and user resources

File Structure:
- /resources/{user_id}/           - User-specific files (strategies, saved analyses)
- /resources/{user_id}/chats/{chat_id}/  - Chat-specific files (temp data, working files)

Strategies are stored as markdown files with embedded code.
"""
import os
from pathlib import Path
from typing import List, Dict, Optional, Literal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manages file resources for users and chat sessions"""
    
    def __init__(self, base_path: str = "resources"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    # ============================================================================
    # Path Helpers
    # ============================================================================
    
    def _get_user_path(self, user_id: str) -> Path:
        """Get user's root directory"""
        path = self.base_path / user_id
        path.mkdir(exist_ok=True)
        return path
    
    def _get_chat_path(self, user_id: str, chat_id: str) -> Path:
        """Get chat-specific directory"""
        path = self._get_user_path(user_id) / "chats" / chat_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def _get_strategies_path(self, user_id: str) -> Path:
        """Get user's strategies directory"""
        path = self._get_user_path(user_id) / "strategies"
        path.mkdir(exist_ok=True)
        return path
    
    # ============================================================================
    # User Files
    # ============================================================================
    
    def write_user_file(self, user_id: str, filename: str, content: str) -> str:
        """
        Write a file to user's directory
        
        Returns: Full path to file
        """
        file_path = self._get_user_path(user_id) / filename
        file_path.write_text(content, encoding='utf-8')
        logger.info(f"Wrote user file: {file_path}")
        return str(file_path)
    
    def read_user_file(self, user_id: str, filename: str) -> Optional[str]:
        """Read a file from user's directory"""
        file_path = self._get_user_path(user_id) / filename
        if not file_path.exists():
            return None
        return file_path.read_text(encoding='utf-8')
    
    def list_user_files(self, user_id: str, pattern: str = "*") -> List[Dict[str, str]]:
        """List files in user's directory"""
        user_path = self._get_user_path(user_id)
        files = []
        for file_path in user_path.glob(pattern):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(self.base_path)),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        return files
    
    def delete_user_file(self, user_id: str, filename: str) -> bool:
        """Delete a file from user's directory"""
        file_path = self._get_user_path(user_id) / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted user file: {file_path}")
            return True
        return False
    
    # ============================================================================
    # Chat Files (Database-backed, Manus-inspired)
    # ============================================================================
    
    def write_chat_file(self, user_id: str, chat_id: str, filename: str, content: str) -> str:
        """
        Write a file to chat (stored in database AND as a resource)
        
        Returns: File ID
        """
        from database import get_db
        from crud.chat_files import create_chat_file
        from crud.resource import create_resource
        
        # Determine file type from extension
        file_type = "text"
        if filename.endswith('.py'):
            file_type = "python"
        elif filename.endswith('.md'):
            file_type = "markdown"
        elif filename.endswith('.csv'):
            file_type = "csv"
        elif filename.endswith('.json'):
            file_type = "json"
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
            file_type = "image"
        
        db = next(get_db())
        try:
            # Create chat file
            file_obj = create_chat_file(
                db=db,
                chat_id=chat_id,
                user_id=user_id,
                filename=filename,
                content=content,
                file_type=file_type
            )
            
            # Also create a resource entry so it shows in the UI sidebar
            create_resource(
                db=db,
                chat_id=chat_id,
                user_id=user_id,
                tool_name="write_chat_file",
                resource_type="file",
                title=filename,
                data={
                    "filename": filename,
                    "file_type": file_type,
                    "size_bytes": file_obj.size_bytes,
                    "file_id": file_obj.id
                },
                resource_metadata={
                    "file_type": file_type,
                    "extension": filename.split('.')[-1] if '.' in filename else 'txt'
                }
            )
            
            return file_obj.id
        finally:
            db.close()
    
    def read_chat_file(self, user_id: str, chat_id: str, filename: str) -> Optional[str]:
        """Read a file from chat (from database)"""
        from database import get_db
        from crud.chat_files import get_chat_file
        
        db = next(get_db())
        try:
            file_obj = get_chat_file(db=db, chat_id=chat_id, filename=filename)
            return file_obj.content if file_obj else None
        finally:
            db.close()
    
    def list_chat_files(self, user_id: str, chat_id: str, pattern: str = "*") -> List[Dict[str, str]]:
        """List files in chat (from database)"""
        from database import get_db
        from crud.chat_files import list_chat_files
        
        db = next(get_db())
        try:
            files_db = list_chat_files(db=db, chat_id=chat_id)
            
            files = []
            for file_obj in files_db:
                # Apply pattern filter if needed
                if pattern != "*":
                    import fnmatch
                    if not fnmatch.fnmatch(file_obj.filename, pattern):
                        continue
                
                files.append({
                    "id": file_obj.id,
                    "name": file_obj.filename,
                    "type": file_obj.file_type,
                    "size": file_obj.size_bytes,
                    "created": file_obj.created_at.isoformat(),
                    "modified": file_obj.updated_at.isoformat(),
                    "description": file_obj.description
                })
            
            return files
        finally:
            db.close()
    
    def delete_chat_file(self, user_id: str, chat_id: str, filename: str) -> bool:
        """Delete a file from chat (from database)"""
        from database import get_db
        from crud.chat_files import delete_chat_file
        
        db = next(get_db())
        try:
            return delete_chat_file(db=db, chat_id=chat_id, filename=filename)
        finally:
            db.close()
    
    # ============================================================================
    # Strategy Files (stored as markdown)
    # ============================================================================
    
    def save_strategy(
        self,
        user_id: str,
        strategy_name: str,
        description: str,
        screening_code: str,
        management_code: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Save a strategy as a markdown file with embedded code
        
        Returns: Path to strategy file
        """
        metadata = metadata or {}
        
        # Sanitize filename
        safe_name = "".join(c for c in strategy_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        filename = f"{safe_name}.md"
        
        # Build markdown content
        content = f"""# Strategy: {strategy_name}

**Created:** {datetime.utcnow().isoformat()}

## Description

{description}

## Configuration

- **Budget:** ${metadata.get('budget', 1000)}
- **Max Positions:** {metadata.get('max_positions', 5)}
- **Position Size:** {metadata.get('position_size_pct', 20)}%
- **Stop Loss:** {metadata.get('stop_loss_pct', 10)}%
- **Take Profit:** {metadata.get('take_profit_pct', 25)}%

## Screening Logic

The screening function evaluates potential buy candidates:

```python
{screening_code}
```

"""
        
        if management_code:
            content += f"""## Position Management Logic

The management function decides when to hold or sell positions:

```python
{management_code}
```

"""
        
        # Write to strategies directory
        strategies_path = self._get_strategies_path(user_id)
        file_path = strategies_path / filename
        file_path.write_text(content, encoding='utf-8')
        
        logger.info(f"Saved strategy: {file_path}")
        return str(file_path)
    
    def get_strategy(self, user_id: str, strategy_name: str) -> Optional[str]:
        """Get strategy markdown file"""
        safe_name = "".join(c for c in strategy_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        filename = f"{safe_name}.md"
        
        strategies_path = self._get_strategies_path(user_id)
        file_path = strategies_path / filename
        
        if not file_path.exists():
            return None
        
        return file_path.read_text(encoding='utf-8')
    
    def list_strategies(self, user_id: str) -> List[Dict[str, str]]:
        """List all strategies for a user"""
        strategies_path = self._get_strategies_path(user_id)
        strategies = []
        
        for file_path in strategies_path.glob("*.md"):
            content = file_path.read_text(encoding='utf-8')
            
            # Extract title from first line
            first_line = content.split('\n')[0]
            title = first_line.replace('# Strategy:', '').strip() if 'Strategy:' in first_line else file_path.stem
            
            strategies.append({
                "name": title,
                "filename": file_path.name,
                "path": str(file_path.relative_to(self.base_path)),
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        return sorted(strategies, key=lambda x: x['modified'], reverse=True)
    
    def delete_strategy(self, user_id: str, strategy_name: str) -> bool:
        """Delete a strategy file"""
        safe_name = "".join(c for c in strategy_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        filename = f"{safe_name}.md"
        
        strategies_path = self._get_strategies_path(user_id)
        file_path = strategies_path / filename
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted strategy: {file_path}")
            return True
        return False


# Global instance
resource_manager = ResourceManager()


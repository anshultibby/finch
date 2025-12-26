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
        
        For images: uploads to Supabase Storage if available, otherwise falls back to base64 in DB
        For text files: stores content directly in database
        
        Returns: File ID
        """
        from database import get_db
        from crud.chat_files import create_chat_file
        from crud.resource import create_resource
        from services.storage import storage_service
        import base64
        
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
        
        # Handle images specially - upload to storage if available
        image_url = None
        file_size = len(content.encode('utf-8'))
        
        if file_type == "image" and storage_service.is_available():
            try:
                # Content is base64-encoded for images
                image_bytes = base64.b64decode(content)
                file_size = len(image_bytes)
                
                # Determine content type
                content_type = "image/png"
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    content_type = "image/jpeg"
                elif filename.lower().endswith('.gif'):
                    content_type = "image/gif"
                elif filename.lower().endswith('.webp'):
                    content_type = "image/webp"
                elif filename.lower().endswith('.svg'):
                    content_type = "image/svg+xml"
                
                # Upload to storage
                image_url = storage_service.upload_image(
                    user_id=user_id,
                    chat_id=chat_id,
                    filename=filename,
                    file_data=image_bytes,
                    content_type=content_type
                )
                
                if image_url:
                    logger.info(f"Uploaded image {filename} to storage: {image_url}")
                    # Don't store base64 content in DB when we have a URL
                    content = None
                else:
                    logger.warning(f"Failed to upload image {filename} to storage, falling back to DB")
            except Exception as e:
                logger.error(f"Error uploading image to storage: {e}", exc_info=True)
                # Fall back to storing base64 in database
        
        db = next(get_db())
        try:
            # Create chat file
            file_obj = create_chat_file(
                db=db,
                chat_id=chat_id,
                user_id=user_id,
                filename=filename,
                content=content,
                file_type=file_type,
                image_url=image_url,
                size_bytes=file_size
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
                    "file_id": file_obj.id,
                    "image_url": image_url  # Include URL in resource data
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
        """Read a file from chat (from database). For text files returns content, for images returns None."""
        from database import get_db
        from crud.chat_files import get_chat_file
        
        db = next(get_db())
        try:
            file_obj = get_chat_file(db=db, chat_id=chat_id, filename=filename)
            return file_obj.content if file_obj else None
        finally:
            db.close()
    
    def read_chat_file_with_metadata(self, user_id: str, chat_id: str, filename: str) -> Optional[Dict]:
        """
        Read a file from chat with full metadata (supports images for multimodal).
        
        Returns:
            Dict with keys:
            - content: str (text content or base64 for images)
            - file_type: str
            - image_url: str (for images stored in Supabase)
            - is_image: bool
        """
        from database import get_db
        from crud.chat_files import get_chat_file
        from services.storage import storage_service
        import base64
        import requests
        
        db = next(get_db())
        try:
            file_obj = get_chat_file(db=db, chat_id=chat_id, filename=filename)
            if not file_obj:
                return None
            
            is_image = file_obj.file_type == "image"
            
            result = {
                "filename": file_obj.filename,
                "file_type": file_obj.file_type,
                "is_image": is_image,
                "image_url": file_obj.image_url,
                "content": file_obj.content
            }
            
            # For images, try to get base64 data for LLM
            if is_image:
                if file_obj.content:
                    # Already have base64 in DB
                    result["image_base64"] = file_obj.content
                elif file_obj.image_url:
                    # Need to fetch from URL and encode
                    try:
                        response = requests.get(file_obj.image_url, timeout=10)
                        if response.status_code == 200:
                            result["image_base64"] = base64.b64encode(response.content).decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Could not fetch image from URL {file_obj.image_url}: {e}")
                
                # Determine media type
                media_type = "image/png"
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    media_type = "image/jpeg"
                elif filename.lower().endswith('.gif'):
                    media_type = "image/gif"
                elif filename.lower().endswith('.webp'):
                    media_type = "image/webp"
                result["media_type"] = media_type
            
            return result
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
        """Delete a file from chat (from database and storage)"""
        from database import get_db
        from crud.chat_files import delete_chat_file, get_chat_file
        from services.storage import storage_service
        
        db = next(get_db())
        try:
            # Check if file is an image with a storage URL
            file_obj = get_chat_file(db=db, chat_id=chat_id, filename=filename)
            if file_obj and file_obj.image_url and storage_service.is_available():
                # Delete from storage
                storage_service.delete_image(user_id, chat_id, filename)
            
            # Delete from database
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


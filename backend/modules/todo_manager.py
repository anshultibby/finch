"""
Todo Manager (Manus-inspired)

Creates and updates todo.md files to track task progress.
Provides visible checklist for users to see what's happening.
"""
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TodoManager:
    """
    Manage todo.md files for task tracking
    
    Manus-style approach:
    - Create todo.md at task start
    - Update markers as items complete: [ ] → [x]
    - Keep file visible for transparency
    - Delete or archive when done (optional)
    """
    
    def create_todo(
        self,
        filepath: str,
        task_title: str,
        items: List[str]
    ) -> None:
        """
        Create a new todo.md file
        
        Args:
            filepath: Full path to todo.md
            task_title: Title/description of the task
            items: List of todo items (without checkboxes)
        """
        content_lines = [
            f"# {task_title}",
            "",
            "Progress checklist:",
            ""
        ]
        
        for item in items:
            content_lines.append(f"- [ ] {item}")
        
        content_lines.append("")
        content_lines.append("---")
        content_lines.append("")
        content_lines.append("*This file tracks progress and will be updated automatically.*")
        
        content = "\n".join(content_lines)
        
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        logger.info(f"Created todo.md: {filepath} with {len(items)} items")
    
    def mark_item_done(
        self,
        filepath: str,
        item_text: str
    ) -> bool:
        """
        Mark a todo item as complete: [ ] → [x]
        
        Args:
            filepath: Path to todo.md
            item_text: Text of the item to mark (partial match ok)
        
        Returns:
            True if item was found and marked, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Find the line with this item
            lines = content.split('\n')
            modified = False
            
            for i, line in enumerate(lines):
                # Check if this line is an unchecked item containing our text
                if '- [ ]' in line and item_text.lower() in line.lower():
                    # Mark it done
                    lines[i] = line.replace('- [ ]', '- [x]', 1)
                    modified = True
                    logger.info(f"Marked done: {item_text}")
                    break
            
            if modified:
                with open(filepath, 'w') as f:
                    f.write('\n'.join(lines))
                return True
            else:
                logger.warning(f"Todo item not found: {item_text}")
                return False
        
        except FileNotFoundError:
            logger.error(f"Todo file not found: {filepath}")
            return False
        except Exception as e:
            logger.error(f"Error updating todo: {str(e)}")
            return False
    
    def add_item(
        self,
        filepath: str,
        item_text: str,
        checked: bool = False
    ) -> bool:
        """
        Add a new item to existing todo.md
        
        Args:
            filepath: Path to todo.md
            item_text: Text of new item
            checked: Whether to add as already checked
        
        Returns:
            True if successful
        """
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Find the separator line (---)
            lines = content.split('\n')
            separator_idx = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('---'):
                    separator_idx = i
                    break
            
            # Insert new item before separator
            checkbox = '[x]' if checked else '[ ]'
            new_item = f"- {checkbox} {item_text}"
            
            if separator_idx >= 0:
                lines.insert(separator_idx, new_item)
            else:
                # No separator, just append
                lines.append(new_item)
            
            with open(filepath, 'w') as f:
                f.write('\n'.join(lines))
            
            logger.info(f"Added item: {item_text}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding item: {str(e)}")
            return False
    
    def get_progress(self, filepath: str) -> dict:
        """
        Get progress summary from todo.md
        
        Returns:
            {
                "total": int,
                "completed": int,
                "progress_pct": float,
                "remaining": List[str]
            }
        """
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            total = 0
            completed = 0
            remaining = []
            
            for line in lines:
                if '- [x]' in line:
                    total += 1
                    completed += 1
                elif '- [ ]' in line:
                    total += 1
                    # Extract item text
                    item = line.replace('- [ ]', '').strip()
                    remaining.append(item)
            
            progress_pct = (completed / total * 100) if total > 0 else 0
            
            return {
                "total": total,
                "completed": completed,
                "progress_pct": round(progress_pct, 1),
                "remaining": remaining
            }
        
        except Exception as e:
            logger.error(f"Error reading progress: {str(e)}")
            return {
                "total": 0,
                "completed": 0,
                "progress_pct": 0,
                "remaining": []
            }
    
    def cleanup(self, filepath: str) -> bool:
        """
        Remove todo.md file (when task complete)
        
        Returns:
            True if deleted successfully
        """
        try:
            Path(filepath).unlink()
            logger.info(f"Cleaned up todo.md: {filepath}")
            return True
        except Exception as e:
            logger.warning(f"Could not delete todo.md: {str(e)}")
            return False


# Global instance
todo_manager = TodoManager()


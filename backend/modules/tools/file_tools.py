"""
File Tools (Manus-inspired)

Advanced file manipulation tools (editing, searching).
Basic file tools (read, write, list) are in strategy_code_tools.py for compatibility.
"""
from modules.tools import tool
from modules.agent.context import AgentContext
from pydantic import BaseModel, Field
from utils.logger import get_logger
import re

logger = get_logger(__name__)


class ReplaceInFileParams(BaseModel):
    """Replace text in a file"""
    filename: str = Field(..., description="Filename in current chat directory")
    old_str: str = Field(..., description="Text to find")
    new_str: str = Field(..., description="Text to replace with")


class FindInFileParams(BaseModel):
    """Search for pattern in file"""
    filename: str = Field(..., description="Filename in current chat directory")
    pattern: str = Field(..., description="Regular expression pattern to search for")


# Note: Basic file tools (read_chat_file, write_chat_file, list_chat_files) 
# are already registered in strategy_code_tools.py for backwards compatibility.
# We only add new advanced tools here.

@tool(
    name="replace_in_chat_file",
    description="""Replace text in a chat file (like Manus's file_str_replace).

**Use for:**
- Fixing code errors
- Updating values/thresholds
- Modifying function logic

**Example:** Replace "growth > 10" with "growth > 20" in code file""",
    category="files"
)
def replace_in_chat_file(
    *,
    params: ReplaceInFileParams,
    context: AgentContext
):
    """Replace text in file"""
    from modules.resource_manager import resource_manager
    
    try:
        # Read file
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            params.filename
        )
        
        if content is None:
            return {
                "success": False,
                "error": f"File '{params.filename}' not found"
            }
        
        # Count occurrences
        count = content.count(params.old_str)
        
        if count == 0:
            return {
                "success": False,
                "error": f"Text not found: '{params.old_str}'"
            }
        
        # Replace
        new_content = content.replace(params.old_str, params.new_str)
        
        # Write back
        path = resource_manager.write_chat_file(
            context.user_id,
            context.chat_id,
            params.filename,
            new_content
        )
        
        return {
            "success": True,
            "filename": params.filename,
            "replacements": count,
            "message": f"Replaced {count} occurrence(s) of '{params.old_str}'"
        }
    
    except Exception as e:
        logger.error(f"Error replacing in file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(
    name="find_in_chat_file",
    description="""Search for pattern in a chat file.

**Use for:**
- Finding function definitions
- Locating specific calculations
- Checking if code uses certain variables

**Returns:** Line numbers and matching text""",
    category="files"
)
def find_in_chat_file(
    *,
    params: FindInFileParams,
    context: AgentContext
):
    """Find pattern in file"""
    from modules.resource_manager import resource_manager
    
    try:
        # Read file
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            params.filename
        )
        
        if content is None:
            return {
                "success": False,
                "error": f"File '{params.filename}' not found"
            }
        
        # Search
        lines = content.split('\n')
        matches = []
        
        for i, line in enumerate(lines):
            if re.search(params.pattern, line):
                matches.append({
                    "line": i,
                    "content": line.strip()
                })
        
        return {
            "success": True,
            "filename": params.filename,
            "pattern": params.pattern,
            "matches": matches,
            "count": len(matches)
        }
    
    except re.error as e:
        return {
            "success": False,
            "error": f"Invalid regex pattern: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error searching file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


# list_chat_files already exists in strategy_code_tools.py


# Database Files Migration

## What Changed

Files are now stored in the **database** instead of the filesystem for better persistence, multi-device access, and proper chat scoping.

## New Schema

### ChatFile Model

```python
class ChatFile(Base):
    __tablename__ = "chat_files"
    
    id = Column(String, primary_key=True)  # UUID
    chat_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # "python", "markdown", "text", "csv"
    content = Column(Text, nullable=False)  # File content
    size_bytes = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
```

**Indexes:**
- `chat_id` - Fast lookups by chat
- `user_id` - List all files for a user
- `(chat_id, filename)` - Unique constraint (one file per name per chat)

## Migration Steps

### 1. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This creates the `chat_files` table with proper indexes.

### 2. Resource Manager Updated

`modules/resource_manager.py` now uses database instead of filesystem:

**Before (Filesystem):**
```python
# Saved to: resources/{user_id}/chats/{chat_id}/file.py
file_path = chat_dir / filename
file_path.write_text(content)
```

**After (Database):**
```python
# Saved to: database.chat_files table
file_obj = create_chat_file(
    db=db,
    chat_id=chat_id,
    user_id=user_id,
    filename=filename,
    content=content
)
```

### 3. New CRUD Operations

`crud/chat_files.py` provides:
- `create_chat_file()` - Create or update file
- `get_chat_file()` - Get file by name
- `list_chat_files()` - List all files in chat
- `delete_chat_file()` - Delete file

### 4. New API Endpoints

`routes/chat_files.py` exposes:

**GET `/api/chat-files/{chat_id}`**
- List all files in a chat
- Returns metadata only (id, filename, size, type, dates)

**GET `/api/chat-files/{chat_id}/download/{filename}`**
- Download file content
- Returns file with proper Content-Type header

**DELETE `/api/chat-files/{chat_id}/{filename}`**
- Delete a file from chat

## Benefits

### ✅ Multi-Device Access
- Files stored centrally in database
- Access from any device
- No need to sync filesystem

### ✅ Proper Chat Scoping
- Files belong to specific chats
- Easy to list all files for a chat
- Automatic cleanup when chat deleted (future)

### ✅ Better UX
- Frontend can list files for each chat
- Users can download generated code
- Files visible in chat sidebar

### ✅ Metadata & Search
- Store file type, description, metadata
- Easy to search/filter files
- Track creation/update times

### ✅ Persistence
- No risk of filesystem cleanup
- Survives server restarts
- Proper backups via database

## Frontend Integration

### List Files for Chat

```typescript
// GET /api/chat-files/{chatId}
const response = await fetch(`/api/chat-files/${chatId}`)
const files = await response.json()
// Returns: [{id, filename, file_type, size_bytes, created_at, ...}]
```

### Download File

```typescript
// GET /api/chat-files/{chatId}/download/{filename}
window.open(`/api/chat-files/${chatId}/download/growth_analysis.py`)
// Downloads file with proper Content-Type
```

### Delete File

```typescript
// DELETE /api/chat-files/{chatId}/{filename}
await fetch(`/api/chat-files/${chatId}/${filename}`, {
    method: 'DELETE'
})
```

## Example Usage

### Code Generation Creates Files

```python
# User: "Create code to analyze revenue growth"

# Tool: generate_financial_code
1. Generates Python code
2. Saves to database:
   - filename: "revenue_growth.py"
   - file_type: "python"
   - content: "def analyze(...)..."
   - chat_id: current chat
   
3. Creates todo.md:
   - filename: "todo.md"
   - file_type: "markdown"  
   - content: "# Generate Code: analyze..."
   - chat_id: current chat

4. Updates todo.md as steps complete

5. Deletes todo.md on success

# User can now:
- See "revenue_growth.py" in chat files list
- Download it
- Execute it on tickers
- Edit it with replace_in_chat_file
```

## File Types

Supported file types:
- `python` - Generated Python code (.py)
- `markdown` - Markdown documents (.md), todo.md
- `text` - Plain text files (.txt)
- `csv` - CSV data exports (.csv)
- `json` - JSON data (.json)

## Backward Compatibility

Old filesystem-based code continues to work:
- `resource_manager.write_chat_file()` now writes to database
- `resource_manager.read_chat_file()` now reads from database  
- `resource_manager.list_chat_files()` now queries database
- Same API, different storage backend

## Migration from Filesystem (Optional)

If you have existing files in `resources/` directory:

```python
# Script to migrate existing files to database
from pathlib import Path
from database import get_db
from crud.chat_files import create_chat_file

def migrate_filesystem_to_db():
    resources_path = Path("resources")
    db = next(get_db())
    
    for user_dir in resources_path.iterdir():
        if not user_dir.is_dir():
            continue
        
        user_id = user_dir.name
        chats_dir = user_dir / "chats"
        
        if not chats_dir.exists():
            continue
        
        for chat_dir in chats_dir.iterdir():
            if not chat_dir.is_dir():
                continue
            
            chat_id = chat_dir.name
            
            for file_path in chat_dir.glob("*"):
                if file_path.is_file():
                    content = file_path.read_text(encoding='utf-8')
                    file_type = "text"
                    if file_path.suffix == ".py":
                        file_type = "python"
                    elif file_path.suffix == ".md":
                        file_type = "markdown"
                    
                    create_chat_file(
                        db=db,
                        chat_id=chat_id,
                        user_id=user_id,
                        filename=file_path.name,
                        content=content,
                        file_type=file_type
                    )
                    print(f"Migrated: {file_path}")
    
    db.close()
```

## Summary

**Old:** Files scattered in filesystem  
**New:** Files centralized in database with proper scoping

**Result:** Better persistence, multi-device access, cleaner UX! 🎉


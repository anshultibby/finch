# File-Based Approach (Manus-Inspired)

## Overview

We now use **file references** instead of passing code strings around. Code is saved to files IMMEDIATELY after generation and all operations work with file paths.

## Key Changes

### Before (String-Based)
```python
# Generate code → get string
code_string = await llm.generate()

# Validate string
validate(code_string)

# Test string (save to temp file just for execution)
with tempfile.NamedTemporaryFile() as f:
    f.write(code_string)
    test(code_string)  # Still passing string

# Save at the end
save_file(code_string)
```

### After (File-Based, Manus Approach)
```python
# Generate code → SAVE TO FILE IMMEDIATELY
file_path = await llm.generate_and_save(save_path="analysis.py")

# Validate FROM FILE
validate(file_path)  # Reads from file

# Test FROM FILE (already saved, just execute)
test(file_path)  # Reads from file, errors show "analysis.py:10"

# File already saved! Just add header if needed
add_metadata_header(file_path)
```

## Benefits

### 1. Better Error Messages ✅
```python
# Before
ValueError in <string> line 10
  ❌ No file reference
  ❌ Can't inspect code easily

# After
ValueError in /path/to/analysis.py line 10
  ✅ Shows exact file
  ✅ Can open file in editor
  ✅ Line numbers match
```

### 2. LLM Can Manipulate Files ✅
```python
# LLM has access to file tools:
read_chat_file(filename="analysis.py")
replace_in_chat_file(
    filename="analysis.py",
    old_str="growth > 10",
    new_str="growth > 20"
)
find_in_chat_file(filename="analysis.py", pattern="def \\w+")
```

### 3. Clean Context Passing ✅
```python
# Before
{
    "code": "def analyze(ticker, data):\n    # 100 lines...",
    "success": True
}

# After
{
    "file_path": "resources/user123/chats/chat456/analysis.py",
    "success": True
}
```

### 4. Incremental Modifications ✅
```python
# LLM can fix errors by editing the file
replace_in_chat_file(
    filename="growth_analysis.py",
    old_str="if growth_pct > threshold:",
    new_str="if growth_pct is not None and growth_pct > threshold:"
)
```

## Implementation

### File Tools (5 tools)

1. **`read_chat_file`** - Read file content
   ```python
   read_chat_file(filename="analysis.py", start_line=10, end_line=20)
   ```

2. **`write_chat_file`** - Create or append to file
   ```python
   write_chat_file(filename="results.txt", content="...", append=True)
   ```

3. **`replace_in_chat_file`** - Replace text (like Manus's file_str_replace)
   ```python
   replace_in_chat_file(
       filename="analysis.py",
       old_str="threshold = 10",
       new_str="threshold = 20"
   )
   ```

4. **`find_in_chat_file`** - Search with regex
   ```python
   find_in_chat_file(filename="analysis.py", pattern="def \\w+")
   ```

5. **`list_chat_files`** - List all files in chat
   ```python
   list_chat_files()  # Returns: ["analysis.py", "todo.md", ...]
   ```

### Code Generation Flow

```
Step 1: Analyze requirements
  → Detect data sources needed
  
Step 2: Generate code
  → LLM creates code
  → SAVE TO FILE IMMEDIATELY: resources/.../analysis.py
  → Return file_path, not code string
  
Step 3: Validate
  → Read from file_path
  → Validate syntax/security
  
Step 4: Test
  → Read from file_path
  → Execute (errors reference file:line)
  
Step 5: Save
  → File already saved!
  → Just add metadata header
```

### Data Flow

```
generate_financial_code(save_as="growth.py")
  ↓
financial_code_generator.generate_code(
    save_path="resources/user/chat/growth.py"  ← File path passed in
)
  ↓
Step 2: _generate_code()
  → code = llm.generate()
  → SAVE: with open(save_path, 'w') as f: f.write(code)
  → return {"file_path": save_path}  ← Return path, not code
  ↓
Step 3: _validate_code(file_path)  ← Path passed
  → with open(file_path) as f: code = f.read()
  → validate(code)
  ↓
Step 4: _test_code(file_path)  ← Path passed
  → with open(file_path) as f: code = f.read()
  → execute(code)  ← Errors show "growth.py:15"
  ↓
Step 5: Done
  → File already at: resources/user/chat/growth.py
```

## File Locations

```
resources/
  {user_id}/
    chats/
      {chat_id}/
        ├── todo.md              # Progress tracking
        ├── growth_analysis.py   # Generated code
        ├── value_screen.py      # Generated code
        └── results.txt          # Analysis output
```

## Comparison to Manus

### Manus Approach
```python
# Manus saves code to working directory
file_write(
    file="/home/ubuntu/analysis.py",
    content=code
)

# Then executes from file
shell_exec(
    id="main",
    exec_dir="/home/ubuntu",
    command="python3 analysis.py"
)
```

### Our Approach
```python
# We save to chat directory (user-visible)
with open("resources/user/chat/analysis.py", 'w') as f:
    f.write(code)

# Execute in sandbox (read from file)
code_sandbox.execute_function(
    open("resources/user/chat/analysis.py").read(),
    "analyze",
    ...
)
```

### Key Differences
- ✅ We save to chat directory (user can see/download)
- ✅ We execute in sandbox (not shell)
- ✅ We provide file tools scoped to chat directory
- ✅ Same principle: file-based execution with file paths

## Example Usage

```python
# User: "Generate code to calculate revenue growth"

# System creates file path
file_path = "resources/user123/chats/chat456/revenue_growth.py"

# Generate and save
await generate_financial_code(
    params={
        "description": "Calculate revenue growth over 3 years",
        "function_name": "calc_growth",
        "save_as": "revenue_growth.py"  # Saves to chat directory
    }
)

# Returns:
{
    "success": True,
    "file_path": "resources/.../revenue_growth.py",  # PRIMARY
    "code": "def calc_growth...",  # For backwards compatibility
    "function_name": "calc_growth"
}

# User can now:
# 1. Read file: read_chat_file(filename="revenue_growth.py")
# 2. Modify file: replace_in_chat_file(...)
# 3. Search file: find_in_chat_file(...)
# 4. Execute file: execute_financial_code(filename="revenue_growth.py", ...)
```

## Benefits Summary

1. **Better debugging** - Errors show file:line numbers
2. **LLM can edit files** - Iterative improvements
3. **Clean context** - Pass file paths, not giant strings
4. **User-visible** - Files saved in chat directory
5. **Manus-aligned** - Follows Manus best practices

**Result:** Clean, debuggable, file-based code generation system.


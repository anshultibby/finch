# Manus Features Integration

Two key Manus principles integrated into financial code generation:

## 1. File-Based Execution ✅

### Why?
**Better error messages with file:line references**

### Before (String Execution)
```python
# Code executed directly from string
result = code_sandbox.execute_function(code_string, "analyze", ...)

# Error: "ValueError in <string> line 10"
# ❌ Can't see which file
# ❌ Hard to debug
```

### After (File-Based Execution)
```python
# Step 1: SAVE code to file FIRST
with open('analysis.py', 'w') as f:
    f.write(code)

# Step 2: THEN execute from file
with open('analysis.py', 'r') as f:
    file_code = f.read()
result = code_sandbox.execute_function(file_code, "analyze", ...)

# Error: "ValueError in /path/to/analysis.py line 10"
# ✅ Shows exact file path
# ✅ Easy to inspect code
# ✅ Better debugging
```

### Implementation

**In `financial_code_generator.py:_test_code()`:**
```python
# Save to file BEFORE running (Manus approach)
if save_path:
    code_path = save_path
    with open(code_path, 'w') as f:
        f.write(code)
else:
    # Use temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        code_path = f.name

# Read and execute FROM file
with open(code_path, 'r') as f:
    file_code = f.read()

result = code_sandbox.execute_function(file_code, function_name, ...)
```

### Benefits
- ✅ Stack traces show `file.py:line` instead of `<string>:line`
- ✅ Code persists for inspection if execution fails
- ✅ Easier to debug with file paths in logs
- ✅ Follows Manus best practice

---

## 2. Todo.md Progress Tracking ✅

### Why?
**Visible progress checklist for users**

### How It Works

**Step 1: Create todo.md at task start**
```markdown
# Generate Code: analyze_growth

Progress checklist:

- [ ] Analyze requirements and identify data needs
- [ ] Generate Python code
- [ ] Validate code (syntax, security)
- [ ] Test with sample data
- [ ] Save code to file

---

*This file tracks progress and will be updated automatically.*
```

**Step 2: Update as steps complete**
```markdown
# Generate Code: analyze_growth

Progress checklist:

- [x] Analyze requirements and identify data needs
- [x] Generate Python code
- [x] Validate code (syntax, security)
- [ ] Test with sample data
- [ ] Save code to file

---

*This file tracks progress and will be updated automatically.*
```

**Step 3: Clean up when done (optional)**
- Delete todo.md on success
- Keep it on failure for debugging

### Implementation

**New file: `todo_manager.py`**
```python
class TodoManager:
    def create_todo(self, filepath, task_title, items):
        """Create todo.md with checklist"""
        
    def mark_item_done(self, filepath, item_text):
        """Update [ ] → [x]"""
        
    def get_progress(self, filepath):
        """Get completion percentage"""
        
    def cleanup(self, filepath):
        """Delete when done"""
```

**In `financial_code_generator.py`:**
```python
# Create todo.md at start
if todo_path:
    todo_items = [step.description for step in plan.steps]
    todo_manager.create_todo(
        filepath=todo_path,
        task_title=f"Generate Code: {function_name}",
        items=todo_items
    )

# Mark items done as we progress
for step in plan.steps:
    # ... execute step ...
    
    if success:
        todo_manager.mark_item_done(todo_path, step.description)
```

**In `financial_code_tools.py`:**
```python
# Todo.md saved to chat directory
todo_path = f"resources/{user_id}/chats/{chat_id}/todo.md"

async for event in financial_code_generator.generate_code(
    task_description=params.description,
    todo_path=todo_path  # Pass path
):
    yield event

# Clean up on success
if final_result.get("success"):
    todo_manager.cleanup(todo_path)
```

### Benefits
- ✅ Users see exact progress in real-time
- ✅ Todo.md visible in chat files list
- ✅ Transparent what's happening at each step
- ✅ Easy to see where failures occurred
- ✅ Follows Manus pattern exactly

---

## File Locations

```
backend/modules/
├── todo_manager.py               # NEW - Todo.md management
├── financial_code_generator.py   # UPDATED - File-based execution + todo tracking
└── tools/
    └── financial_code_tools.py   # UPDATED - Creates todo.md, cleans up
```

---

## Example Flow

```
User: "Calculate revenue growth and profit margins"
  ↓
Tool: generate_financial_code
  ↓
1. Create todo.md in chat directory:
   resources/user123/chats/chat456/todo.md
   
2. Execute agent loop:
   
   Step 1/5: Analyze requirements
     → Update todo.md: [x] Analyze requirements
     
   Step 2/5: Generate code
     → Update todo.md: [x] Generate Python code
     
   Step 3/5: Validate
     → Update todo.md: [x] Validate code
     
   Step 4/5: Test
     → SAVE to file: resources/.../growth_analysis.py
     → READ from file
     → EXECUTE from file (better errors!)
     → Update todo.md: [x] Test with sample data
     
   Step 5/5: Save
     → Update todo.md: [x] Save code to file
     
3. All steps complete!
   → Delete todo.md (task done)
   → Return final code

User can see todo.md during execution for transparency
```

---

## Comparison to Original Manus

### Manus Approach
- Creates `todo.md` in working directory
- Updates with text replacement tool
- Rebuilds when plans change
- Verifies completion before cleanup

### Our Implementation
- ✅ Creates `todo.md` in chat directory (user-visible)
- ✅ Updates programmatically (no LLM calls)
- ✅ Automatically marks items done
- ✅ Cleans up on success

### Differences
- ❌ We don't rebuild todo.md (fixed 5-step plan)
- ❌ We don't use it for replanning (simpler scope)
- ✅ We integrate with chat file system
- ✅ We auto-cleanup (less manual work)

---

## Testing

```python
# Test todo manager
from modules.todo_manager import todo_manager

# Create
todo_manager.create_todo(
    filepath="/tmp/test_todo.md",
    task_title="Test Task",
    items=["Step 1", "Step 2", "Step 3"]
)

# Mark done
todo_manager.mark_item_done("/tmp/test_todo.md", "Step 1")

# Check progress
progress = todo_manager.get_progress("/tmp/test_todo.md")
# Returns: {"total": 3, "completed": 1, "progress_pct": 33.3, ...}

# Cleanup
todo_manager.cleanup("/tmp/test_todo.md")
```

---

## Benefits Summary

### File-Based Execution
1. Better error messages (file:line)
2. Code persists for debugging
3. Follows Manus best practice
4. More professional approach

### Todo.md Tracking
1. Visible progress for users
2. Transparent execution
3. Easy debugging (see where it failed)
4. Professional UX

**Result:** Clean, transparent, debuggable code generation with Manus-inspired best practices.


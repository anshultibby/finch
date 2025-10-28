# UX Improvements: Ephemeral Tool Call Messages & Resources Sidebar

## Overview
This implementation adds two major UX improvements:
1. **Ephemeral tool call messages** that show users when functions are being called
2. **Resources sidebar** that stores all function results for easy navigation

## Architecture

### Backend Changes

#### 1. Database Schema (`006_create_resources.py`)
- Created `resources` table to store function call results
- Added `resource_id` column to `chat_messages` table (FK to resources)
- Resources are linked to messages via foreign key from messages

#### 2. Models
- **`Resource` model** (db.py): Stores function result data as JSONB
- **Pydantic models** (resource.py): `ResourceResponse`, `ResourceMetadata`, `ToolCallStatus`
- Updated `ChatResponse` to include `tool_calls` field

#### 3. CRUD Operations
- `crud/resource.py`: Create, read, delete resources
- `crud/chat.py`: Updated to link messages to resources

#### 4. Agent Changes (`agent.py`)
- Modified `process_message` to return tool call information
- Modified `_handle_tool_calls` to track tool execution status
- Returns tuple: `(response, needs_auth, messages, tool_calls_info)`

#### 5. Chat Service (`chat_service.py`)
- Creates resources for each successful tool call
- Maps tool results to appropriate resource types and titles
- Links tool message responses to resources via `resource_id`
- Returns tool call metadata to API

#### 6. API Routes
- **`routes/resources.py`**: New endpoints for resource management
  - `GET /resources/chat/{chat_id}` - Get all resources for a chat
  - `GET /resources/user/{user_id}` - Get all user resources
  - `GET /resources/{resource_id}` - Get specific resource
  - `DELETE /resources/{resource_id}` - Delete resource
- **Updated `routes/chat.py`**: Returns tool call information in response

### Frontend Changes

#### 1. Types & API Client (`lib/api.ts`)
- Added `ToolCallStatus` interface
- Added `Resource` and `ResourceMetadata` interfaces
- Added `resourcesApi` with CRUD operations
- Updated `ChatResponse` to include `tool_calls`

#### 2. Components

##### ResourcesSidebar (`components/ResourcesSidebar.tsx`)
- Sliding sidebar from the right
- Displays all resources with icons, titles, and timestamps
- Filter by resource type
- Click to view resource details

##### ResourceViewer (`components/ResourceViewer.tsx`)
- Modal for viewing resource details
- Shows metadata (parameters, creation time)
- Shows full JSON data with syntax highlighting
- Copy JSON button

##### Updated ChatContainer (`components/ChatContainer.tsx`)
- **Ephemeral tool call messages**: Show function calls as they happen with status
- **Resources button**: Badge showing count of resources
- **Auto-reload resources**: Fetches resources after tool calls complete
- **Integration**: Connects sidebar and viewer components

## User Experience Flow

### 1. Function Calls (Ephemeral Messages)
```
User: "review my portfolio"
  ↓
[Ephemeral Message Appears]
📊 get_portfolio
✓ Completed [View →]
  ↓
Assistant: "Here's your portfolio analysis..."
  ↓
[Ephemeral message fades after 5 seconds]
```

### 2. Resources Sidebar
```
User clicks "Resources" button (badge shows count)
  ↓
Sidebar slides in from right
  ↓
Shows all function results as browseable list:
- 📊 Portfolio Holdings (2m ago)
- 📱 Top 10 Trending Stocks on Reddit (5m ago)
- 💼 Recent Insider Trades (8m ago)
  ↓
User clicks any resource
  ↓
Modal opens with full JSON data
```

### 3. Resource Types

Resources are automatically categorized:
- **Portfolio** 📊: `get_portfolio`
- **Reddit** 📱: `get_reddit_trending_stocks`, `get_reddit_ticker_sentiment`
- **Congressional** 🏛️: `get_recent_senate_trades`, `get_recent_house_trades`
- **Insider Trading** 💼: All insider trading tools
- **Other** 📄: Any other tool

## Data Storage

### Why PostgreSQL JSONB (not GCS)?
- Resources stored as JSONB in PostgreSQL
- Fast querying and filtering
- No external dependencies
- Efficient for data up to ~5MB per resource
- Can migrate to GCS later if needed for very large results

### Resource Metadata
Each resource includes:
- `tool_name`: Function that generated it
- `resource_type`: Category for filtering
- `title`: Human-readable name
- `data`: Full function result (JSONB)
- `metadata`: Parameters used, tool_call_id, execution time
- `created_at`: Timestamp

## Migration

To apply the database changes:
```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

## Benefits

1. **Transparency**: Users see what functions are being called in real-time
2. **Exploration**: Users can browse and review all data fetched
3. **Context**: Resources persist across the session for reference
4. **No GCS needed**: PostgreSQL JSONB handles storage efficiently
5. **Extensible**: Easy to add new resource types and viewers

## Future Enhancements

Possible additions:
1. Resource search and filtering
2. Export resources as CSV/JSON
3. Resource sharing (generate shareable links)
4. Resource comparison view
5. Move to GCS for very large resources (>5MB)
6. Custom resource viewers for different data types (tables, charts)
7. Resource analytics (most viewed, most useful)


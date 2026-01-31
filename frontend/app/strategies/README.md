# Strategy Management UI

Comprehensive UI for managing automated trading strategies built with Next.js and TypeScript.

## Overview

The `/strategies` page provides users with a complete interface to:
- View all their automated trading bots
- Monitor real-time performance and execution
- Manage strategy settings and capital allocation
- Track progress from paper to live trading
- View detailed execution history and logs

## Architecture

### Component Structure

```
app/strategies/
├── page.tsx                      # Main page with filters, search, and layout
└── components/
    ├── StrategyCard.tsx          # Strategy list item with quick stats
    ├── StrategyDetails.tsx       # Main details panel with tabs
    ├── EmptyState.tsx            # No strategies state
    ├── CapitalMeter.tsx          # Visual capital allocation display
    ├── TrackRecordProgress.tsx   # Paper trading graduation progress
    ├── index.ts                  # Component exports
    └── tabs/
        ├── OverviewTab.tsx       # Thesis, capital, entry/exit, performance
        ├── CodeTab.tsx           # View entry.py, exit.py, config.json
        ├── HistoryTab.tsx        # Execution timeline with logs
        ├── PerformanceTab.tsx    # Charts and metrics
        └── SettingsTab.tsx       # Mode, capital, and danger zone
```

## Features

### 1. Two-Column Layout

**Left Column (30%)**: Strategy list
- Strategy cards with quick stats
- Search bar
- Filters (status, mode, platform)
- Sort options (name, P&L, win rate, created date)

**Right Column (70%)**: Selected strategy details
- 5 tabs: Overview, Code, History, Performance, Settings

### 2. Strategy Card

Displays:
- Name and thesis
- Status badge (Active/Paused/Needs Approval)
- Mode badge (Live/Paper/Backtest)
- Quick stats (Total Trades, Win Rate, P&L)
- Capital meter (deployed/available)
- Execution frequency
- Action buttons (Enable/Pause, Test, View)

### 3. Overview Tab

Shows:
- Approval status banner
- Investment thesis
- Platform and mode badges
- Capital allocation meter with positions
- Entry/Exit condition cards
- Paper trading progress (if in paper mode)
- Performance summary cards
- Risk limits

### 4. Code Tab

Features:
- Collapsible code sections for entry.py, exit.py, config.json
- Syntax highlighting
- Copy to clipboard
- "Edit in Chat" button
- Last modified timestamp

### 5. Execution History Tab

Displays:
- Timeline of all executions
- Filter by status (All/Success/Failed)
- Expandable execution cards showing:
  - Status icon and duration
  - Mode badge
  - Signals generated
  - Actions taken
  - Execution logs
  - Error messages (if failed)

### 6. Performance Tab

Shows:
- Summary cards (Total P&L, Win Rate, Sharpe Ratio, Max Drawdown)
- Performance by mode table (Backtest/Paper/Live)
- Trade statistics (Avg Win/Loss, Largest Win/Loss)
- Best/Worst trades
- Chart placeholder (ready for Plotly/Recharts integration)

### 7. Settings Tab

Includes:
- Execution mode selector
- Live trading graduation criteria
- Editable capital settings:
  - Total Capital
  - Capital Per Trade
  - Max Positions
  - Max Daily Loss
- Execution frequency slider
- Danger zone:
  - Pause/Resume strategy
  - Delete strategy (with confirmation)

## Data Flow

### API Integration

All strategy operations use `strategiesApi` from `/lib/api.ts`:

```typescript
- listStrategies(userId)           // Get all strategies
- getStrategy(userId, strategyId)  // Get single strategy
- updateStrategy(userId, strategyId, data)  // Update settings
- runStrategy(userId, strategyId, dryRun)   // Execute strategy
- getExecutions(userId, strategyId, limit)  // Get execution history
- deleteStrategy(userId, strategyId)        // Delete strategy
```

### Type Definitions

Extended types in `/lib/types/index.ts`:

```typescript
- Strategy: Main strategy object with config and stats
- StrategyConfig: Configuration including capital, platform, scripts
- StrategyStats: Performance metrics across all modes
- CapitalAllocation: Capital management settings
- StrategyExecution: Execution record with logs and actions
```

## Key Features Implemented

### ✅ Phase 1: MVP
- Two-column responsive layout
- Strategy cards with basic info
- Overview tab with thesis and capital
- Enable/pause toggle
- Empty state

### ✅ Phase 2: History & Monitoring
- Execution history timeline
- Log viewer with syntax highlighting
- Expandable execution cards
- Real-time polling support (ready for WebSocket)

### ✅ Phase 3: Performance & Analytics
- Performance metrics by mode
- Mode breakdown table
- Trade statistics
- Best/worst trades display

### ✅ Phase 4: Code Viewing
- Syntax highlighted code display
- Copy to clipboard
- "Edit in Chat" functionality
- Collapsible code sections

### ✅ Phase 5: Settings & Control
- Graduation criteria checker
- Capital allocation editor
- Mode switching controls
- Strategy deletion with confirmation

### ✅ Phase 6: Polish & UX
- Search and filters
- Sort options
- Mobile responsive design
- Loading states
- Empty states

## Design System

### Colors
- **Live**: `bg-green-100 text-green-800` (#10B981)
- **Paper**: `bg-blue-100 text-blue-800` (#3B82F6)
- **Backtest**: `bg-gray-100 text-gray-800` (#6B7280)
- **Paused**: `bg-gray-100 text-gray-600`
- **Needs Approval**: `bg-yellow-100 text-yellow-800` (#F59E0B)
- **Error**: `bg-red-100 text-red-800` (#EF4444)
- **Success**: `bg-green-100 text-green-800` (#10B981)

### Typography
- Strategy name: `text-lg font-semibold`
- Thesis: `text-xs text-gray-500 italic`
- Metrics: `text-2xl font-bold`
- Labels: `text-xs text-gray-500 uppercase tracking-wide`

### Spacing
- Cards: `p-4` with `space-y-3`
- Sections: `mb-6`
- Tabs: `px-6 py-4`

## Mobile Responsiveness

The UI is fully responsive:
- Single column layout on mobile
- Touch-optimized buttons
- Swipeable tabs
- Sticky header
- Full-width capital meters
- Stacked filter/sort controls

## Future Enhancements

### Real-time Updates (Phase 7)
- WebSocket integration for live execution logs
- Toast notifications for important events
- Auto-refresh on strategy execution

### Advanced Analytics (Phase 8)
- Plotly/Recharts integration
- Cumulative P&L chart
- Trade distribution histogram
- Performance heatmaps

### Additional Features
- Bulk actions (pause/resume all)
- Strategy comparison view
- Export to CSV/JSON
- Strategy templates/examples
- Quick actions menu (⋮)

## Usage Example

```tsx
import StrategiesPage from '@/app/strategies/page';

// Navigate to strategies page
router.push('/strategies');

// Auto-loads user's strategies
// Auto-selects first strategy
// Shows comprehensive details panel
```

## Testing Checklist

- [ ] Load strategies list
- [ ] Select strategy
- [ ] Toggle enable/pause
- [ ] Run dry run
- [ ] View all tabs
- [ ] Edit capital settings
- [ ] Graduate to live (with criteria met)
- [ ] Filter by status/mode/platform
- [ ] Search strategies
- [ ] Sort strategies
- [ ] Delete strategy
- [ ] Mobile layout
- [ ] Empty state

## Dependencies

All components use existing dependencies:
- React 18
- Next.js 14
- TypeScript
- Tailwind CSS
- No additional packages required

## Notes

- Code viewing shows mock data - real implementation will fetch from ChatFiles
- Chart placeholder ready for Plotly/Recharts integration
- WebSocket support ready - just needs backend endpoint
- All graduation criteria implemented and functional
- Fully type-safe with TypeScript

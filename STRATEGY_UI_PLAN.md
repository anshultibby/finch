# Strategy UI Implementation Plan

## Overview
Build a comprehensive UI at `/strategies` for users to view, manage, test, and analyze their automated trading bots.

---

## 1. Strategy Management Page (`/strategies`)

### Layout: Two-Column Design

**Left Column (30%)**: Strategy Cards List
- Card for each strategy showing:
  - Name + Thesis (truncated)
  - Status badge: 🟢 Live | 📝 Paper | 🧪 Backtest | ⏸️ Paused | ⚠️ Needs Approval
  - Mode badge: Shows current execution mode
  - Quick stats (3 metrics in row):
    - Total Trades
    - Win Rate (green if >55%, red if <45%)
    - P&L (green if positive, red if negative)
  - Capital meter: Visual bar showing deployed/available
    - e.g., "$450 / $5,000" with colored bar
  - Execution frequency: "⏱️ Every 60s"
  - Action buttons:
    - Toggle: Enable/Pause
    - Test: Run dry run
    - View: Select for details

**Right Column (70%)**: Strategy Details Panel
- Shows selected strategy with tabs:
  1. Overview
  2. Code
  3. Execution History
  4. Performance
  5. Settings

---

## 2. Strategy Details Tabs

### Tab 1: Overview
**Content:**
- **Header Section:**
  - Strategy name (editable)
  - Thesis in highlighted box
  - Platform badge (Polymarket/Kalshi/Alpaca)
  - Current mode chip (Backtest/Paper/Live)
  
- **Capital Allocation Card:**
  ```
  Total Capital: $5,000
  ├── Deployed:   $450  (9%)  [█░░░░░░░░░]
  ├── Available:  $4,550 (91%)
  └── Per Trade:  $100
  
  Positions: 3 / 5 max
  ```

- **Entry/Exit Conditions:**
  - Two side-by-side cards:
    - 🚪 Entry: `entry_description` text
    - 🚪 Exit: `exit_description` text

- **Track Record Progress:**
  If mode is Paper:
  ```
  📊 Paper Trading Progress
  ┌─────────────────────────────────────┐
  │ ████████░░░░░░░░░░░░░░░░░░ 15/20    │ trades completed
  │ Win Rate: 73% ✅ (need >55%)        │
  │ P&L: +$125.50 ✅                     │
  │ Max Drawdown: -8% ✅ (limit 20%)    │
  └─────────────────────────────────────┘
  Status: ⏳ 5 more trades to graduate to live
  [Graduate to Live] button (enabled when criteria met)
  ```

### Tab 2: Code
**Content:**
- Three collapsible code viewers:
  1. **entry.py** - Syntax highlighted Python
  2. **exit.py** - Syntax highlighted Python  
  3. **config.json** - Formatted JSON
- Each has:
  - Copy button
  - "Edit in Chat" button (opens chat with prepopulated message)
  - Last modified timestamp
- Read-only display (editing happens through chat)

### Tab 3: Execution History
**Content:**
- Timeline view of all executions (most recent first)
- Each execution card shows:
  - Timestamp + duration
  - Status: ✅ Success | ❌ Failed | ⏳ Running
  - Mode: 🧪 Backtest | 📝 Paper | 🟢 Live
  - Summary: "Found 2 signals, entered 1 position, exited 0"
  - Expandable sections:
    - **Logs** (terminal-style, monospace):
      ```
      [12:34:56] 🔍 Checking 3 traders for new activity...
      [12:34:57] 📊 0x742d35... has 5 recent trades
      [12:34:57] 🔔 NEW TRADE from 0x742d35...
      [12:34:58] 💵 Position size: $100.00
      [12:34:59] ✅ Order placed: token_id abc123...
      ```
    - **Signals** (structured cards for each entry/exit signal)
    - **Actions** (list of orders placed/cancelled)
    - **Errors** (if any, in red box)
- Pagination (20 per page)
- Filter dropdown: All | Success | Failed | By Mode

### Tab 4: Performance
**Content:**
- **Summary Cards (row of 4):**
  - Total P&L (large number, green/red)
  - Win Rate (percentage with trend arrow)
  - Sharpe Ratio (if available)
  - Max Drawdown (percentage)

- **Mode Breakdown Table:**
  ```
  Mode      | Trades | Win Rate | P&L      | Status
  ──────────┼────────┼──────────┼──────────┼────────
  Backtest  | 50     | 68%      | +$450    | ✅ Complete
  Paper     | 15     | 73%      | +$125    | ⏳ In Progress
  Live      | 0      | -        | -        | 🔒 Locked
  ```

- **Performance Chart:**
  - Line chart: Cumulative P&L over time
  - X-axis: Date
  - Y-axis: P&L in USD
  - Color-coded by mode (gray=backtest, blue=paper, green=live)
  - Hover shows: Date, P&L, Trade details

- **Trade Distribution:**
  - Histogram: P&L per trade
  - Shows distribution of wins vs losses

- **Best/Worst Trades:**
  - Two cards side by side:
    - 🏆 Best Trade: Market name, P&L, date
    - 💀 Worst Trade: Market name, P&L, date

### Tab 5: Settings
**Content:**
- **Execution Mode:**
  ```
  Current Mode: Paper Trading
  
  [Backtest] [Paper] [Live] (tabs/pills)
  
  ⚠️ Live trading requires:
  - ✅ 20+ paper trades (15/20)
  - ✅ 55%+ win rate (73%)
  - ✅ Positive P&L (+$125)
  - ❌ <20% max drawdown (8%)
  
  [Switch to Live] (disabled until ready)
  ```

- **Capital Settings:**
  - Editable fields:
    - Total Capital
    - Capital Per Trade
    - Max Positions
    - Position Sizing Method (dropdown: Fixed | Kelly | % Capital)
    - Max Daily Loss
  - [Save Changes] button

- **Execution Settings:**
  - Execution Frequency slider (10s to 300s)
  - Live preview: "Checks every 60 seconds"

- **Danger Zone:**
  - [Pause Strategy] / [Resume Strategy]
  - [Delete Strategy] (with confirmation modal)

---

## 3. Empty State (No Strategies Yet)

**Full-page centered design:**
```
        🤖
   No Strategies Yet
   
Create your first automated trading bot
      with AI assistance

   [Create Strategy in Chat]
   
Or check out examples:
• Copy Top Traders
• Sports Betting Bot
• Congress Trading Bot
```

---

## 4. Strategy Creation Flow (from Chat)

**User in chat:** "Create a bot to copy Polymarket trader X"

**AI generates code → Shows in chat:**
```
✅ Strategy Created: "Copy Top Traders"

📝 Thesis: Copy trades from proven successful traders

Files generated:
• entry.py (47 lines)
• exit.py (28 lines)  
• config.json

Capital: $5,000 total, $100 per trade
Platform: Polymarket
Frequency: Every 60 seconds

[View in Strategies] [Deploy Now]
```

**On Deploy:**
1. Saves files as ChatFiles
2. Creates Strategy record (enabled=false, approved=false)
3. Redirects to `/strategies` with new strategy selected
4. Shows approval banner: "⚠️ Review and approve before enabling"

---

## 5. Top Navigation Integration

**Update `/strategies` nav button:**
- Shows badge with active strategy count: "🤖 Bots (3)"
- Badge color:
  - Green dot: Has active live strategies
  - Blue dot: Only paper/backtest
  - Gray: No active strategies

---

## 6. Mobile Responsive Design

**Mobile Layout:**
- Single column (no side-by-side)
- Strategy cards in vertical list
- Tap card → Full-screen details view
- Bottom nav for tabs (swipeable)
- Sticky header with back button
- Capital meter shows as full-width bar
- Charts adapt to mobile (smaller, simplified)

---

## 7. Real-time Updates

**WebSocket Integration:**
- Connect to `/ws/strategies/{strategy_id}`
- Live updates when strategy executes:
  - New execution appears in history
  - P&L updates in real-time
  - Capital deployed/available updates
  - Log messages stream to Execution History tab
- Toast notifications for important events:
  - "Strategy placed new order: $100 on Market XYZ"
  - "Strategy closed position: +$15 profit"
  - "Strategy graduation eligible!"

---

## 8. Additional Features

### Quick Actions Menu (⋮ button on each card)
- Edit in Chat
- Run Test
- View Performance
- Duplicate Strategy
- Export Code
- Delete

### Bulk Actions (when multiple selected)
- Pause All
- Resume All
- Compare Performance

### Filters & Sort (top of left column)
- Filter by:
  - Status: All | Active | Paused | Needs Approval
  - Mode: All | Backtest | Paper | Live
  - Platform: All | Polymarket | Kalshi | Alpaca
- Sort by:
  - Name (A-Z)
  - P&L (High to Low)
  - Win Rate (High to Low)
  - Created Date (Newest First)

### Search Bar
- Search by strategy name or thesis keywords
- Real-time filtering

---

## 9. Component Structure (Frontend)

```
app/strategies/
├── page.tsx                    # Main page component
└── components/
    ├── StrategyCard.tsx        # Left column card
    ├── StrategyDetails.tsx     # Right panel container
    ├── tabs/
    │   ├── OverviewTab.tsx
    │   ├── CodeTab.tsx
    │   ├── HistoryTab.tsx
    │   ├── PerformanceTab.tsx
    │   └── SettingsTab.tsx
    ├── ExecutionCard.tsx       # Individual execution in history
    ├── CapitalMeter.tsx        # Visual capital allocation bar
    ├── TrackRecordProgress.tsx # Paper trading progress widget
    ├── PerformanceChart.tsx    # P&L line chart
    └── EmptyState.tsx          # No strategies view
```

---

## 10. API Endpoints Needed

All already exist or defined:

```typescript
// Already have:
strategiesApi.listStrategies(userId)
strategiesApi.getStrategy(userId, strategyId)
strategiesApi.updateStrategy(userId, strategyId, data)
strategiesApi.runStrategy(userId, strategyId, dryRun)
strategiesApi.getExecutions(userId, strategyId, limit)
strategiesApi.deleteStrategy(userId, strategyId)

// May need to add:
strategiesApi.graduateToLive(userId, strategyId)
strategiesApi.getPerformanceMetrics(userId, strategyId)
strategiesApi.getStrategyCode(userId, strategyId) // get entry/exit code
```

---

## 11. Implementation Order

### Phase 1: Basic View (MVP)
1. Create `/strategies` page with two-column layout
2. Build StrategyCard component with basic info
3. Build Overview tab (thesis, capital, entry/exit descriptions)
4. Add enable/pause toggle
5. Wire up to existing backend endpoints

### Phase 2: History & Monitoring
1. Build Execution History tab with timeline
2. Add log viewer with syntax highlighting
3. Implement execution card expand/collapse
4. Add real-time updates via polling (every 5s when viewing)

### Phase 3: Performance & Analytics
1. Build Performance tab with charts
2. Add Plotly/Recharts for P&L visualization
3. Implement mode breakdown table
4. Add best/worst trades display

### Phase 4: Code Viewing
1. Build Code tab with syntax highlighting
2. Add copy to clipboard
3. Add "Edit in Chat" functionality
4. Show last modified timestamps

### Phase 5: Settings & Control
1. Build Settings tab
2. Add graduation criteria checker
3. Implement capital allocation editor
4. Add mode switching controls

### Phase 6: Polish & UX
1. Add empty state design
2. Implement filters and search
3. Add mobile responsiveness
4. Add WebSocket for real-time updates
5. Add toast notifications
6. Add loading states and skeletons

---

## 12. Design System

**Colors:**
- Live: `#10B981` (green-500)
- Paper: `#3B82F6` (blue-500)
- Backtest: `#6B7280` (gray-500)
- Paused: `#F59E0B` (amber-500)
- Error: `#EF4444` (red-500)
- Success: `#10B981` (green-500)

**Typography:**
- Strategy name: `text-lg font-semibold`
- Thesis: `text-sm text-gray-600 italic`
- Metrics: `text-2xl font-bold`
- Labels: `text-xs text-gray-500 uppercase tracking-wide`

**Spacing:**
- Cards: `p-4` with `space-y-3`
- Sections: `mb-6`
- Tabs: `px-6 py-4`

---

## Success Criteria

✅ User can see all their strategies at a glance
✅ User can monitor strategy execution in real-time
✅ User understands strategy performance (P&L, win rate)
✅ User can easily enable/pause strategies
✅ User knows when strategy is ready to go live
✅ User can view and understand strategy code
✅ User feels confident strategy is working (through logs/transparency)
✅ Mobile experience is functional

---

## Next Steps

1. Copy this plan
2. Start new chat: "Implement strategy UI based on attached plan"
3. Focus on Phase 1 (MVP) first
4. Iterate based on user feedback

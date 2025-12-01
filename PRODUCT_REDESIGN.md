# Finch Product Redesign - User Flow & Architecture

## 🎯 Vision
A clean, intuitive interface that separates **strategy management** from **conversational AI**, while seamlessly connecting them through contextual chat modes.

---

## 🏗️ Architecture Overview

### **View Hierarchy**

```
┌─────────────────────────────────────────────────────────────┐
│                    Main App Layout                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Header: Logo | Tab Nav | Account | Profile          │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                        │   │
│  │   📊 STRATEGIES VIEW  |  💬 CHAT VIEW  |  📈 ANALYTICS│   │
│  │                                                        │   │
│  │   (Tab-based navigation - only one visible at a time) │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📱 View Specifications

### **1. Strategies View** (Default Landing)

**Purpose:** Manage, view, and execute trading strategies

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  🎯 Your Trading Strategies                                 │
│                                                              │
│  [+ Create New Strategy]  [Import Strategy]  [📊 Stats]     │
│  ────────────────────────────────────────────────────────── │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Strategy Card 1   │  │ Strategy Card 2   │               │
│  │ ──────────────── │  │ ──────────────── │                │
│  │ Name, Desc        │  │ Name, Desc        │               │
│  │ Risk Params       │  │ Risk Params       │               │
│  │ Last Run: 2d ago  │  │ Last Run: Never   │               │
│  │                   │  │                   │                │
│  │ [▶ Run] [Edit]    │  │ [▶ Run] [Edit]    │               │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  (Grid layout, 2-3 per row, scrollable)                     │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- `StrategiesView.tsx` (new)
- `StrategyCard.tsx` (new)
- `StrategyStats.tsx` (new)

**Actions:**
1. **Create New Strategy** → Navigate to Chat View with mode="create_strategy"
2. **Run Strategy** → Navigate to Chat View with mode="execute_strategy" + strategyId
3. **Edit Strategy** → Navigate to Chat View with mode="edit_strategy" + strategyId
4. **View Details** → Expand card or show modal with full strategy details

---

### **2. Chat View**

**Purpose:** Conversational AI interface with contextual modes

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  [Context Banner - shows current mode]                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 🎯 Creating New Strategy                             │   │
│  │ I'll help you design a trading strategy...           │   │
│  │                                         [← Strategies] │   │
│  └──────────────────────────────────────────────────────┘   │
│  ────────────────────────────────────────────────────────── │
│                                                              │
│  [Chat Messages Area]                                       │
│  - AI and User messages                                     │
│  - Tool execution indicators                                │
│  - Strategy execution progress                              │
│  - Results/visualizations                                   │
│                                                              │
│  ────────────────────────────────────────────────────────── │
│  [Chat Input - contextual placeholder based on mode]        │
└─────────────────────────────────────────────────────────────┘
```

**Modes:**

1. **General Mode** (default)
   - Banner: Hidden or minimal "💬 Chat with Finch"
   - Placeholder: "Ask about your portfolio, market trends, or strategies..."
   - Full access to all tools

2. **Strategy Creation Mode** (`mode="create_strategy"`)
   - Banner: "🎯 Creating New Strategy | [← Back to Strategies]"
   - Placeholder: "Describe the type of strategy you want to create..."
   - System prompt enhanced with strategy creation context
   - On completion: Show success banner with link back to Strategies

3. **Strategy Execution Mode** (`mode="execute_strategy"`)
   - Banner: "⚡ Running: [Strategy Name] | [← Back to Strategies]"
   - Placeholder: Disabled or "Strategy is executing..."
   - Real-time execution updates via SSE
   - Progress indicators for each phase
   - On completion: Show results, link back to Strategies

4. **Strategy Edit Mode** (`mode="edit_strategy"`)
   - Banner: "✏️ Editing: [Strategy Name] | [← Back to Strategies]"
   - Placeholder: "What would you like to change?"
   - Pre-loads strategy details
   - Shows current config

5. **Performance Analysis Mode** (`mode="analyze_performance"`)
   - Banner: "📊 Analyzing Your Trading Performance | [← Chat]"
   - Focused on trade analysis, patterns, insights
   - Can be triggered from Analytics view (future)

**Components:**
- `ChatView.tsx` (refactored from ChatContainer)
- `ChatModeContext.tsx` (new - manages mode state)
- `ChatModeBanner.tsx` (new)

---

### **3. Analytics View** (Future - Phase 2)

**Purpose:** Performance dashboard, trade journal, insights

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Performance Dashboard                                    │
│                                                              │
│  [Time Period: YTD ▼]                                        │
│  ────────────────────────────────────────────────────────── │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Total   │ │ Win     │ │ Avg Win │ │ Profit  │           │
│  │ Return  │ │ Rate    │ │         │ │ Factor  │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                              │
│  [Portfolio Value Chart]                                    │
│                                                              │
│  [Trade Journal Table]                                      │
│  ────────────────────────────────────────────────────────── │
│  │ Date   │ Symbol │ Type │ P&L     │ Grade │ [Analyze]   │ │
│  │ 12/01  │ AAPL   │ SELL │ +$1,234 │   A   │ [→]         │ │
│  │ 11/28  │ TSLA   │ SELL │ -$432   │   D   │ [→]         │ │
│                                                              │
│  [Ask AI about this →] - Opens Chat in Analysis mode        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 State Management

### **Chat Mode State**

```typescript
// contexts/ChatModeContext.tsx
interface ChatMode {
  type: 'general' | 'create_strategy' | 'execute_strategy' | 'edit_strategy' | 'analyze_performance';
  metadata?: {
    strategyId?: string;
    strategyName?: string;
    tradeId?: string;
    // ... other context
  };
}

interface ChatModeContextType {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
  clearMode: () => void;
  isInSpecialMode: boolean;
}
```

### **Navigation State**

```typescript
// Use Next.js router or simple state
type View = 'strategies' | 'chat' | 'analytics';

interface NavigationState {
  currentView: View;
  navigateTo: (view: View, chatMode?: ChatMode) => void;
}
```

---

## 🎬 User Flow Examples

### **Flow 1: New User Onboarding**

```
1. User lands on app → Strategies View (empty state)
2. Sees: "Welcome! Create your first trading strategy"
3. Clicks "Create New Strategy"
4. → Chat View opens with creation mode
5. AI: "Let's create your first strategy! What type of stocks interest you?"
6. User interacts, answers questions
7. Strategy created → Success banner: "✓ Strategy Created! View in Strategies →"
8. User clicks banner → Returns to Strategies View
9. Strategy card now visible
```

### **Flow 2: Execute Existing Strategy**

```
1. User on Strategies View
2. Clicks "Run" on "Tech Momentum" strategy
3. → Chat View opens with execution mode
4. Banner: "⚡ Running: Tech Momentum Strategy"
5. AI starts execution:
   - "Screening candidates from S&P 500..."
   - "Found 47 candidates, applying rules..."
   - "✓ 12 BUY signals, 3 SELL signals"
   - Shows decisions with reasoning
6. Execution complete → Banner: "✓ Complete - View Results ↓"
7. User can:
   - Review results in chat
   - Click banner to return to Strategies
   - Continue chatting about results
```

### **Flow 3: Quick Portfolio Question**

```
1. User clicks "Chat" tab
2. Chat View opens in general mode
3. Types: "What's my portfolio worth?"
4. AI responds with current value
5. User continues: "Show me my best performing stock"
6. AI analyzes and responds
7. User navigates back to Strategies when done
```

### **Flow 4: Analyze a Trade**

```
1. User on Analytics View (future)
2. Sees trade: TSLA -$432 (Grade: D)
3. Clicks "Analyze" button
4. → Chat View opens with analyze_performance mode
5. Banner: "📊 Analyzing TSLA Trade from Nov 28"
6. AI provides detailed analysis:
   - What went wrong
   - Optimal exit point
   - Lessons learned
7. User can ask follow-up questions
8. Returns to Analytics when done
```

---

## 🎨 UI Components Structure

### **New Components to Create**

```
frontend/components/
├── layout/
│   ├── AppLayout.tsx              (Main layout with tab nav)
│   └── TabNavigation.tsx          (Tab switcher)
│
├── strategies/
│   ├── StrategiesView.tsx         (Main strategies page)
│   ├── StrategyCard.tsx           (Individual strategy card)
│   ├── StrategyGrid.tsx           (Grid layout for cards)
│   ├── CreateStrategyButton.tsx   (CTA button)
│   └── StrategyStats.tsx          (Quick stats summary)
│
├── chat/
│   ├── ChatView.tsx               (Refactored ChatContainer)
│   ├── ChatModeBanner.tsx         (Context banner component)
│   └── (existing chat components)
│
└── analytics/ (future)
    ├── AnalyticsView.tsx
    ├── PerformanceCards.tsx
    └── TradeJournal.tsx
```

### **Contexts**

```
frontend/contexts/
├── AuthContext.tsx       (existing)
├── ChatModeContext.tsx   (new - manages chat mode state)
└── NavigationContext.tsx (new - manages view state)
```

---

## 🚀 Implementation Plan

### **Phase 1: Core Infrastructure** (Week 1)

- [ ] Create AppLayout with tab navigation
- [ ] Create NavigationContext for view management
- [ ] Create ChatModeContext for mode management
- [ ] Update routing structure

### **Phase 2: Strategies View** (Week 1-2)

- [ ] Create StrategiesView component
- [ ] Create StrategyCard component
- [ ] Create StrategyGrid layout
- [ ] Add "Create New Strategy" flow
- [ ] Add "Run Strategy" → Chat navigation

### **Phase 3: Chat Refactor** (Week 2)

- [ ] Refactor ChatContainer → ChatView
- [ ] Add mode support (props/context)
- [ ] Create ChatModeBanner component
- [ ] Update chat to handle different modes
- [ ] Add navigation helpers (back buttons)

### **Phase 4: Integration** (Week 2-3)

- [ ] Wire up strategy creation flow
- [ ] Wire up strategy execution flow
- [ ] Test all navigation paths
- [ ] Polish UI/UX transitions
- [ ] Add loading states

### **Phase 5: Analytics View** (Week 3-4)

- [ ] Create AnalyticsView (performance dashboard)
- [ ] Add trade journal
- [ ] Add performance metrics
- [ ] Connect to Chat for analysis

---

## 🎯 Success Criteria

### **User Experience**
- [ ] Clear separation between strategy management and chat
- [ ] Seamless transitions between views
- [ ] Context is always clear (mode banners)
- [ ] No confusion about "where am I?"
- [ ] Back navigation always works

### **Developer Experience**
- [ ] Clean component hierarchy
- [ ] Proper state management
- [ ] Type-safe navigation
- [ ] Easy to add new views/modes

### **Performance**
- [ ] Fast view transitions
- [ ] No unnecessary re-renders
- [ ] Smooth animations

---

## 💡 Future Enhancements

1. **Deep Linking**
   - Direct URLs to specific strategies
   - Share strategy execution results
   - Bookmark specific chats

2. **Mobile Responsive**
   - Bottom nav for mobile
   - Swipe between views
   - Optimized for small screens

3. **Notifications**
   - Strategy execution complete
   - New trading opportunities
   - Portfolio alerts

4. **Collaboration**
   - Share strategies with friends
   - Community strategies library
   - Compare performance

---

## 📊 Key Metrics to Track

- Time spent in each view
- Strategy creation completion rate
- Strategy execution frequency
- Chat engagement in different modes
- User satisfaction scores
- Feature adoption rates

---

**Next Step:** Start implementation with Phase 1 (Core Infrastructure)


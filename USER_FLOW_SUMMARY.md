# Finch - Redesigned User Flow (Quick Summary)

## 🎯 Core Concept

**Two Primary Views + Contextual Chat** instead of modals

---

## 📱 The New Interface

```
┌────────────────────────────────────────────────────┐
│  Finch  [📊 Strategies] [💬 Chat] [📈 Analytics]  │  ← Tab Navigation
├────────────────────────────────────────────────────┤
│                                                     │
│  STRATEGIES VIEW (Landing Page)                    │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ Strategy 1   │  │ Strategy 2   │               │
│  │ ──────────   │  │ ──────────   │               │
│  │ Tech Stocks  │  │ Value Play   │               │
│  │ Active       │  │ Paused       │               │
│  │              │  │              │               │
│  │ [▶ Run]      │  │ [▶ Run]      │               │
│  └──────────────┘  └──────────────┘               │
│                                                     │
│  [+ Create New Strategy]                           │
└────────────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────────────┐
│  Finch  [📊 Strategies] [💬 Chat] [📈 Analytics]  │
├────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐ │
│  │ ⚡ Running: Tech Momentum Strategy           │ │  ← Context Banner
│  │                        [← Back to Strategies]│ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  CHAT VIEW (with execution mode)                   │
│  ┌───────────────────────────────────────────────┐│
│  │ 🤖 Screening 500 candidates...                ││
│  │ ✓ Found 47 matching criteria                  ││
│  │                                                ││
│  │ 👤 Show me the BUY signals                    ││
│  │                                                ││
│  │ 🤖 Here are 12 BUY signals:                   ││
│  │    • NVDA - Strong momentum, +15% revenue...  ││
│  │    • AMD - Breakout pattern...                ││
│  └───────────────────────────────────────────────┘│
│  [Type your message...]                            │
└────────────────────────────────────────────────────┘
```

---

## 🔄 Key User Flows

### **1. Create Strategy**
```
Strategies View
    ↓ [Click "Create New Strategy"]
Chat View (Creation Mode)
    → AI guides through questions
    → Strategy saved
    ↓ [Click "← Back to Strategies"]
Strategies View (new strategy appears)
```

### **2. Run Strategy**
```
Strategies View
    ↓ [Click "Run" on a strategy]
Chat View (Execution Mode)
    → Shows live progress
    → Displays decisions & reasoning
    → Results appear
    ↓ [Click "← Back to Strategies"]
Strategies View
```

### **3. General Chat**
```
Any View
    ↓ [Click "Chat" tab]
Chat View (General Mode)
    → Ask anything
    → Regular portfolio Q&A
```

---

## ✨ Key Benefits

### **vs Current Modal Approach:**
- ✅ **More Space**: Full screen for complex workflows
- ✅ **Better Context**: Clear which mode you're in
- ✅ **Easier Navigation**: Tabs instead of modal layers
- ✅ **Persistent State**: Each view maintains its state
- ✅ **Scalable**: Easy to add more views (Analytics, Settings)

### **vs Single Chat View:**
- ✅ **Organized**: Strategies have their own home
- ✅ **Discoverable**: See all strategies at a glance
- ✅ **Purposeful**: Each view has a clear purpose
- ✅ **Less Cluttered**: Chat isn't overloaded

---

## 🎨 Visual Hierarchy

```
Level 1: Tab Navigation
    ├─ Strategies (Primary - users manage their strategies)
    ├─ Chat (Secondary - AI assistance)
    └─ Analytics (Future - performance insights)

Level 2: View Content
    Strategies View:
        ├─ Strategy Cards (visual, scannable)
        ├─ Quick Actions (Run, Edit, Create)
        └─ Stats Summary
    
    Chat View:
        ├─ Mode Banner (context indicator)
        ├─ Messages (conversation)
        └─ Input (contextual)

Level 3: Modal Overlays (when needed)
    └─ Account Management (keep as modal - less frequently used)
```

---

## 🚀 Implementation Phases

### **Phase 1** (Week 1): Infrastructure
- Tab navigation
- View routing
- Context management

### **Phase 2** (Week 1-2): Strategies View
- Strategy cards
- Grid layout
- Navigation to chat

### **Phase 3** (Week 2): Chat Refactor
- Mode support
- Context banners
- Back navigation

### **Phase 4** (Week 2-3): Integration
- Wire everything together
- Polish transitions
- Testing

### **Phase 5** (Week 3-4): Analytics View
- Performance dashboard
- Trade journal
- Connect to chat

---

## 💭 Design Decisions Explained

**Why Tabs Instead of Sidebar?**
- Cleaner on mobile
- Forces focus on one thing at a time
- Standard pattern users understand

**Why Full Views Instead of Modals?**
- Strategy creation/execution are complex workflows
- Need more screen real estate
- Better for displaying results/data

**Why Keep Mode Banners in Chat?**
- Users need context when coming from other views
- Easy way to navigate back
- Shows what the AI is focused on

**Why Strategies as Default Landing?**
- Most important feature (strategies are the product)
- Encourages engagement
- Shows value immediately
- Chat is a tool to support strategies, not the main feature

---

## 🎯 Success Looks Like

1. **User lands** → Sees their strategies (or create one)
2. **User creates strategy** → Smooth flow via chat
3. **User runs strategy** → Clear execution in chat
4. **User switches views** → Fast, intuitive
5. **User returns** → Remembers where they were

---

## 🤔 Open Questions for Discussion

1. **Should we keep the current modal for Account Management?**
   - Pro: Less frequently used, doesn't need full view
   - Con: Inconsistent with strategy management

2. **Should strategy execution auto-navigate to chat or stay in strategies?**
   - Option A: Auto-navigate (current proposal)
   - Option B: Show inline in strategies view with expandable results

3. **Should we add a "Home" view with dashboard/overview?**
   - Or keep Strategies as the landing page?

4. **What about Resources sidebar?**
   - Keep as sidebar in chat?
   - Move to its own tab?
   - Keep in both chat + analytics?

---

**Ready to start implementing?** 🚀

Let's begin with Phase 1: Creating the tab navigation and view routing infrastructure.


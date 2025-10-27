# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Setup (One-time)
```bash
# Run the setup script
./setup.sh

# Or manually:
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Step 2: Configure
Add your OpenAI API key to `backend/.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### Step 3: Run

**Easy Way:**
```bash
# Terminal 1
./start-backend.sh

# Terminal 2
./start-frontend.sh
```

**Or start both at once** (requires tmux):
```bash
./start-all.sh
```

**Manual Way:**
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python main.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Visit: **http://localhost:3000**

---

## 🎯 What You Can Do

- Ask general investment questions
- Get portfolio management advice
- Learn about market concepts
- Practice conversational portfolio queries

## 🔧 Next: Add Robinhood Integration

The app is ready for tool calling! To add Robinhood:

1. Install robin-stocks: `pip install robin-stocks`
2. Add your Robinhood credentials to `.env`
3. Define tools in `backend/agent.py`
4. Implement tool handlers

Example tools to add:
- `get_portfolio()` - Fetch current holdings
- `get_stock_price(symbol)` - Get real-time prices
- `get_portfolio_performance()` - Performance metrics
- `place_order(symbol, quantity, side)` - Execute trades

## 📚 Documentation

- Full docs: `README.md`
- Backend docs: `backend/README.md`
- Frontend docs: `frontend/README.md`
- API docs: `http://localhost:8000/docs` (when backend is running)

## 💡 Tips

- Use `http://localhost:8000/docs` for API testing
- Check browser console for frontend errors
- Backend logs appear in the terminal
- Press Enter to send, Shift+Enter for new line in chat

## 🐛 Common Issues

**"Module not found" errors:**
```bash
cd frontend && npm install
```

**"API connection failed":**
- Ensure backend is running on port 8000
- Check that NEXT_PUBLIC_API_URL is correct in `.env.local`

**"Invalid API key":**
- Verify your OPENAI_API_KEY in `backend/.env`
- Make sure there are no extra spaces or quotes

---

Enjoy building with Finch! 🐦✨


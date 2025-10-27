# Finch - Portfolio Chatbot

A modern AI-powered chatbot for managing and chatting with your investment portfolio. Built with FastAPI backend and Next.js frontend.

## 🚀 Features

- **AI-Powered Chat**: Conversational interface powered by Claude (Anthropic)
- **Modern UI**: Beautiful, responsive interface built with Next.js and Tailwind CSS
- **Session Management**: Persistent chat sessions with history
- **Extensible Architecture**: Ready for Robinhood API integration via tool calls
- **Real-time Responses**: Fast and efficient communication between frontend and backend

## 📋 Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn
- OpenAI API key (get from [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys))

## 🛠️ Installation

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory:
```bash
cp .env.example .env
```

5. Add your OpenAI API key to the `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Create a `.env.local` file (optional, uses default if not set):
```bash
cp .env.local.example .env.local
```

## 🚀 Running the Application

### Easy Way: Use the Start Scripts

**Option 1: Start Backend**
```bash
./start-backend.sh
```

**Option 2: Start Frontend** (in a new terminal)
```bash
./start-frontend.sh
```

**Option 3: Start Both** (requires tmux)
```bash
./start-all.sh
```

The scripts will:
- ✅ Check and create virtual environments
- ✅ Install dependencies
- ✅ Create .env files from templates
- ✅ Validate configuration
- ✅ Start the services

### Manual Way

**Start the Backend:**

From the `backend` directory:
```bash
source venv/bin/activate
python main.py
```

The API will be available at `http://localhost:8000`

You can verify it's running by visiting:
- `http://localhost:8000` - Root endpoint
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/docs` - Interactive API documentation (FastAPI Swagger UI)

**Start the Frontend:**

From the `frontend` directory:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## 📁 Project Structure

```
finch/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── agent.py             # AI agent implementation
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment variables template
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Main page
│   │   ├── layout.tsx       # Root layout
│   │   └── globals.css      # Global styles
│   ├── components/
│   │   ├── ChatContainer.tsx # Main chat component
│   │   ├── ChatMessage.tsx   # Message component
│   │   └── ChatInput.tsx     # Input component
│   ├── lib/
│   │   └── api.ts            # API client
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.js
└── README.md
```

## 🔧 API Endpoints

### POST `/chat`
Send a message to the chatbot
```json
{
  "message": "What's my portfolio performance?",
  "session_id": "optional-session-id"
}
```

### GET `/chat/history/{session_id}`
Retrieve chat history for a session

### DELETE `/chat/history/{session_id}`
Clear chat history for a session

### GET `/health`
Health check endpoint

## 🎨 Customization

### Changing the AI Model

The backend uses Claude by default. To switch to OpenAI:

1. Uncomment the OpenAI implementation in `backend/agent.py`
2. Update `requirements.txt` to include `openai`
3. Add your OpenAI API key to `.env`

### Styling

The frontend uses Tailwind CSS. Customize colors in `frontend/tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Your custom colors
      },
    },
  },
}
```

## 🔌 Adding Tool Calls (Robinhood Integration)

The agent is structured to support tool calling. To add Robinhood integration:

1. Install robin-stocks: `pip install robin-stocks`
2. Define tool schemas in `backend/agent.py`
3. Implement tool handlers for portfolio queries and trading actions
4. Update the agent's system prompt with tool descriptions

Example tool structure:
```python
tools = [
    {
        "name": "get_portfolio",
        "description": "Get current portfolio holdings",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    }
]
```

## 🐛 Troubleshooting

### Backend Issues

- **Import errors**: Make sure you activated the virtual environment
- **API key errors**: Verify your `.env` file has the correct API key
- **Port already in use**: Change the port in `main.py`

### Frontend Issues

- **Module not found**: Run `npm install` again
- **API connection errors**: Ensure backend is running on port 8000
- **Build errors**: Delete `.next` folder and `node_modules`, then reinstall

## 📝 Development Tips

- Use `http://localhost:8000/docs` for interactive API testing
- Check browser console for frontend errors
- Backend logs will show in the terminal running the server
- Use React DevTools for component debugging

## 🤝 Contributing

This is a personal project, but feel free to fork and customize for your needs!

## 📄 License

See LICENSE file for details.

## 🔮 Roadmap

- [ ] Robinhood API integration
- [ ] Real-time portfolio updates
- [ ] Chart visualizations
- [ ] Trading capabilities via chat
- [ ] Portfolio analytics and insights
- [ ] Authentication and user management
- [ ] Database persistence
- [ ] Deployment configurations

#!/bin/bash

echo "🐦 Starting Finch Portfolio Chatbot..."
echo ""

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "Using tmux to run both services..."
    echo ""
    
    # Create a new tmux session
    tmux new-session -d -s finch

    # Backend (top-left)
    tmux send-keys -t finch "cd $(pwd) && ./start-backend.sh" C-m

    # Web frontend (top-right)
    tmux split-window -h -t finch
    tmux send-keys -t finch "cd $(pwd) && sleep 3 && ./start-frontend.sh" C-m

    # Mobile (Expo) — set MOBILE=0 to skip it
    if [ "${MOBILE:-1}" != "0" ]; then
        tmux split-window -v -t finch
        tmux send-keys -t finch "cd $(pwd) && sleep 3 && ./start-mobile.sh" C-m
    fi

    # Tidy, even layout across panes
    tmux select-layout -t finch tiled
    tmux select-pane -t 0

    echo "✅ Services starting in tmux session 'finch'"
    echo ""
    echo "📝 To attach to the session: tmux attach -t finch"
    echo "📝 To detach: Press Ctrl+B then D"
    echo "📝 To stop: tmux kill-session -t finch"
    echo ""
    
    # Attach to the session
    tmux attach -t finch
    
else
    echo "⚠️  tmux not found. Starting services in separate terminals..."
    echo ""
    echo "Please run these commands in separate terminals:"
    echo ""
    echo "Terminal 1: ./start-backend.sh"
    echo "Terminal 2: ./start-frontend.sh"
    echo "Terminal 3: ./start-mobile.sh   # optional — Expo dev server"
    echo ""
    echo "Or install tmux: brew install tmux (macOS) / apt install tmux (Linux)"
fi


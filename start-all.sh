#!/bin/bash

echo "🐦 Starting Finch Portfolio Chatbot..."
echo ""

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "Using tmux to run both services..."
    echo ""
    
    # Create a new tmux session
    tmux new-session -d -s finch
    
    # Split window horizontally
    tmux split-window -h
    
    # Run backend in left pane
    tmux select-pane -t 0
    tmux send-keys "cd $(pwd) && ./start-backend.sh" C-m
    
    # Run frontend in right pane
    tmux select-pane -t 1
    tmux send-keys "cd $(pwd) && sleep 3 && ./start-frontend.sh" C-m
    
    echo "✅ Both services starting in tmux session 'finch'"
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
    echo ""
    echo "Or install tmux: brew install tmux (macOS) / apt install tmux (Linux)"
fi


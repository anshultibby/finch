#!/usr/bin/env python3
"""Quick script to check chat history statistics"""
import sys
from models.chat_history import ChatHistory
from database import SessionLocal
from models.db import ChatMessage

chat_id = "a5b3a4d2-6ed7-4920-8fb8-7abe08c8c280"

db = SessionLocal()
try:
    messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.sequence).all()
    
    if not messages:
        print(f"No messages found for chat {chat_id}")
    else:
        history = ChatHistory.from_db_messages(messages, chat_id=chat_id, user_id="user")
        history.print_statistics()
finally:
    db.close()

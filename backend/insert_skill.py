import sqlite3
import uuid
from datetime import datetime

# Read skill content
with open('/Users/anshul/code/finch/backend/skill_content.md', 'r') as f:
    content = f.read()

# Connect to database
conn = sqlite3.connect('/Users/anshul/code/finch/backend/finch.db')
cursor = conn.cursor()

# Check if skill already exists
cursor.execute("SELECT id FROM global_skills WHERE id = 'polymarket-top-traders-001'")
existing = cursor.fetchone()

if existing:
    # Update existing skill
    cursor.execute("""
        UPDATE global_skills
        SET name = ?, description = ?, content = ?, updated_at = ?
        WHERE id = 'polymarket-top-traders-001'
    """, (
        'Polymarket Top Traders & Kalshi Arbitrage',
        'Find top-performing wallets on Polymarket using DOME API, analyze their trading strategies, and identify corresponding arbitrage opportunities on Kalshi. Use this skill when users ask about copy trading, finding profitable traders, or cross-platform prediction market opportunities.',
        content,
        datetime.now().isoformat()
    ))
    print("Updated existing skill")
else:
    # Insert new skill
    cursor.execute("""
        INSERT INTO global_skills (id, name, description, content, category, is_official, author_user_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'polymarket-top-traders-001',
        'Polymarket Top Traders & Kalshi Arbitrage',
        'Find top-performing wallets on Polymarket using DOME API, analyze their trading strategies, and identify corresponding arbitrage opportunities on Kalshi. Use this skill when users ask about copy trading, finding profitable traders, or cross-platform prediction market opportunities.',
        content,
        'trading',
        True,
        'system',
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ))
    print("Created new skill")

conn.commit()
conn.close()
print("Done!")

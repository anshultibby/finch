"""Add system skills - migrate from servers to unified skills model

Revision ID: 026
Revises: 025
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None

# System skills to seed
SYSTEM_SKILLS = [
    {
        "id": "skill_dome",
        "name": "dome",
        "description": "Polymarket & Kalshi prediction market data APIs. Access market prices, wallet positions, trading history, and find arbitrage opportunities across prediction markets.",
        "category": "prediction_markets",
        "is_official": True
    },
    {
        "id": "skill_polygon_io",
        "name": "polygon_io",
        "description": "Stock market data from Polygon.io. Real-time and historical prices, intraday bars, company fundamentals, and market snapshots for US equities.",
        "category": "stock_data",
        "is_official": True
    },
    {
        "id": "skill_financial_modeling_prep",
        "name": "financial_modeling_prep",
        "description": "Stock fundamentals, financial statements, ownership data, and analyst estimates from Financial Modeling Prep. Company profiles, insider trading, institutional ownership, and more.",
        "category": "stock_fundamentals",
        "is_official": True
    },
    {
        "id": "skill_kalshi_trading",
        "name": "kalshi_trading",
        "description": "Trade on Kalshi prediction markets. Place orders, manage positions, check portfolio balance. Requires API key authentication.",
        "category": "trading",
        "is_official": True
    },
    {
        "id": "skill_tradingview",
        "name": "tradingview",
        "description": "Technical analysis and chart generation from TradingView. Multi-timeframe analysis, trend alignment, and embeddable charts with indicators.",
        "category": "technical_analysis",
        "is_official": True
    },
    {
        "id": "skill_snaptrade",
        "name": "snaptrade",
        "description": "Connect and manage brokerage accounts via SnapTrade. View portfolio holdings, account balances, and trade history across multiple brokers.",
        "category": "brokerage",
        "is_official": True
    },
    {
        "id": "skill_reddit",
        "name": "reddit",
        "description": "Social sentiment analysis from Reddit. Track trending stock mentions, sentiment scores, and discussion volume across subreddits.",
        "category": "sentiment",
        "is_official": True
    },
    {
        "id": "skill_strategies",
        "name": "strategies",
        "description": "Deploy and manage automated trading strategies. Create, deploy, backtest, and monitor algorithmic trading bots that run on schedules.",
        "category": "automation",
        "is_official": True
    }
]


def upgrade():
    # Add is_system column to global_skills table
    op.add_column('global_skills', sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create index for system skills
    op.create_index('idx_global_skills_system', 'global_skills', ['is_system'])
    
    # Note: System skills are seeded via a script after migration
    # This allows the skill content to be loaded from SKILL.md files


def downgrade():
    # Drop index
    op.drop_index('idx_global_skills_system', table_name='global_skills')
    
    # Drop column
    op.drop_column('global_skills', 'is_system')

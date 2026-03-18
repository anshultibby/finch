"""
Trading bot ORM models: TradingBot, BotFile, BotExecution, BotPosition, BotWakeup, TradeLog
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from core.database import Base
import uuid


class TradingBot(Base):
    """
    LLM-driven trading bot owned by a user.
    """
    __tablename__ = "trading_bots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    icon = Column(String(10), nullable=True)
    directory = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=False, default=False, index=True)
    config = Column(JSONB, nullable=False, default=dict)
    stats = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<TradingBot(id='{self.id}', name='{self.name}', enabled={self.enabled})>"


class BotFile(Base):
    """
    Files owned by a trading bot: context, memory, notes, or code.
    """
    __tablename__ = "bot_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bot_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    file_type = Column(String, nullable=False, default="code")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<BotFile(id='{self.id}', bot='{self.bot_id}', filename='{self.filename}', type='{self.file_type}')>"


class BotExecution(Base):
    """Audit log of bot tick executions."""
    __tablename__ = "bot_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    data = Column(JSONB, nullable=False, default=dict)

    def __repr__(self):
        return f"<BotExecution(id='{self.id}', bot='{self.bot_id}', status='{self.status}')>"


class BotPosition(Base):
    """An open or closed position held by a trading bot."""
    __tablename__ = "bot_positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    market = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    side = Column(String, nullable=False)
    market_title = Column(String, nullable=True)
    event_ticker = Column(String, nullable=True)
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    quantity = Column(Float, nullable=False)
    cost_usd = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="open", index=True)
    exit_config = Column(JSONB, nullable=False, default=dict)
    entered_via = Column(UUID(as_uuid=True), nullable=True)
    closed_via = Column(UUID(as_uuid=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    exit_price = Column(Float, nullable=True)
    realized_pnl_usd = Column(Float, nullable=True)
    close_reason = Column(String, nullable=True)
    current_price = Column(Float, nullable=True)
    unrealized_pnl_usd = Column(Float, nullable=True)
    last_priced_at = Column(DateTime(timezone=True), nullable=True)
    price_history = Column(JSONB, nullable=False, default=list)
    monitor_note = Column(Text, nullable=True)
    paper = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<BotPosition(id='{self.id}', bot='{self.bot_id}', market='{self.market}', status='{self.status}')>"


class BotWakeup(Base):
    """
    Scheduled wake-up for a trading bot.
    """
    __tablename__ = "bot_wakeups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    trigger_at = Column(DateTime(timezone=True), nullable=False, index=True)
    trigger_type = Column(String, nullable=False, default="custom")
    reason = Column(Text, nullable=False)
    context = Column(JSONB, nullable=False, default=dict)
    status = Column(String, nullable=False, default="pending", index=True)
    chat_id = Column(String, nullable=True)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    recurrence = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<BotWakeup(id='{self.id}', bot='{self.bot_id}', trigger_at='{self.trigger_at}', status='{self.status}')>"


class TradeLog(Base):
    """
    Audit log of every trade order attempted by a bot.
    """
    __tablename__ = "trade_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    execution_id = Column(UUID(as_uuid=True), nullable=True)
    position_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String, nullable=False)
    market = Column(String, nullable=False)
    market_title = Column(String, nullable=True)
    platform = Column(String, nullable=False, default="kalshi")
    side = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    realized_pnl_usd = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="executed", index=True)
    approval_token = Column(String, nullable=True, index=True)
    approval_method = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    order_response = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    dry_run = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<TradeLog(id='{self.id}', bot='{self.bot_id}', action='{self.action}', market='{self.market}', status='{self.status}')>"

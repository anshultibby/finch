"""
Strategy V2 API routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from models.strategy_v2 import TradingStrategyV2, StrategyExecutionResult
from crud.strategy_v2 import get_user_strategies, get_chat_strategies, get_strategy, get_budget, get_positions
from services.strategy_executor import StrategyExecutor
from services.candidate_selector import CandidateSelector
from database import SessionLocal
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

# Initialize services
strategy_executor = StrategyExecutor()
candidate_selector = CandidateSelector()


# Disabled strategy fetching endpoints
# @router.get("/{user_id}/{chat_id}", response_model=List[TradingStrategyV2])
# async def get_chat_strategies_endpoint(
#     user_id: str,
#     chat_id: str,
#     active_only: bool = Query(True, description="Only return active strategies")
# ):
#     """
#     Get all strategies for a specific chat
#     """
#     db = SessionLocal()
#     try:
#         strategies = get_chat_strategies(db, chat_id, active_only=active_only)
#         return strategies
#     except Exception as e:
#         logger.error(f"Error fetching strategies for chat {chat_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         db.close()


# @router.get("/{user_id}", response_model=List[TradingStrategyV2])
# async def get_all_user_strategies(
#     user_id: str,
#     active_only: bool = Query(True, description="Only return active strategies")
# ):
#     """
#     Get all strategies for a user (across all chats)
#     """
#     db = SessionLocal()
#     try:
#         strategies = get_user_strategies(db, user_id, active_only=active_only)
#         return strategies
#     except Exception as e:
#         logger.error(f"Error fetching strategies for user {user_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         db.close()


@router.get("/{user_id}/{strategy_id}", response_model=TradingStrategyV2)
async def get_strategy_by_id(user_id: str, strategy_id: str):
    """
    Get a specific strategy by ID
    """
    db = SessionLocal()
    try:
        strategy = get_strategy(db, strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        if strategy.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return strategy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching strategy {strategy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/{user_id}/{strategy_id}/execute")
async def execute_strategy(user_id: str, strategy_id: str):
    """
    Execute a strategy (run screening and management rules)
    
    This will:
    1. Screen candidates based on candidate_source
    2. Manage existing positions
    3. Return decisions with BUY/SELL/HOLD signals
    """
    db = SessionLocal()
    try:
        # Get strategy
        strategy = get_strategy(db, strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        if strategy.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not strategy.is_active:
            raise HTTPException(status_code=400, detail="Strategy is not active")
        
        logger.info(f"Executing strategy '{strategy.name}' (ID: {strategy_id}) for user {user_id}")
        
        # Get budget and positions
        budget = get_budget(db, strategy_id)
        positions = get_positions(db, strategy_id, open_only=True)
        
        if not budget:
            raise HTTPException(
                status_code=400, 
                detail="Strategy budget not initialized. Create strategy budget first."
            )
        
        # Execute screening rules on candidates
        screening_decisions = []
        
        # Use LLM-powered candidate selector (max 10)
        candidate_tickers = await candidate_selector.select_candidates(strategy, max_candidates=10)
        
        logger.info(f"Selected {len(candidate_tickers)} candidates: {candidate_tickers}")
        
        # Screen all selected candidates
        for ticker in candidate_tickers:
            try:
                decision = await strategy_executor.screen_candidate(strategy, ticker)
                screening_decisions.append(decision)
            except Exception as e:
                logger.error(f"Error screening {ticker}: {str(e)}")
        
        # Execute management rules on positions
        management_decisions = []
        
        logger.info(f"Managing {len(positions)} positions")
        
        for position in positions:
            try:
                decision = await strategy_executor.manage_position(strategy, position)
                management_decisions.append(decision)
            except Exception as e:
                logger.error(f"Error managing position {position.ticker}: {str(e)}")
        
        # Build result
        result = StrategyExecutionResult(
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            timestamp=datetime.utcnow(),
            screening_decisions=screening_decisions,
            management_decisions=management_decisions,
            budget=budget,
            positions=positions
        )
        
        logger.info(
            f"Strategy execution complete: {result.buy_signals} BUY, "
            f"{result.sell_signals} SELL, {result.hold_signals} HOLD"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error executing strategy {strategy_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# Old candidate selection removed - now using CandidateSelector service


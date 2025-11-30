"""
Portfolio analytics and performance calculations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
from database import SessionLocal
from crud import transactions as tx_crud
from sqlalchemy import func, and_
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Calculate portfolio performance metrics"""
    
    def calculate_performance_metrics(
        self,
        user_id: str,
        period: str = "all_time"
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        
        Args:
            user_id: User ID
            period: Time period (all_time, ytd, 1m, 3m, 6m, 1y)
            
        Returns:
            PerformanceMetrics dictionary
        """
        db = SessionLocal()
        try:
            # Get date range for period
            start_date = self._get_period_start_date(period)
            
            # Get all transactions in period
            transactions = tx_crud.get_transactions(
                db, user_id, start_date=start_date
            )
            
            if not transactions:
                return self._empty_metrics(user_id, period)
            
            # Calculate closed positions using FIFO
            closed_positions = self._calculate_closed_positions(transactions)
            
            if not closed_positions:
                return self._empty_metrics(user_id, period)
            
            # Calculate metrics
            metrics = {
                "user_id": user_id,
                "period": period,
                "calculated_at": datetime.now().isoformat()
            }
            
            # Win/Loss stats
            winners = [p for p in closed_positions if p["realized_pnl"] > 0]
            losers = [p for p in closed_positions if p["realized_pnl"] < 0]
            
            metrics["total_trades"] = len(closed_positions)
            metrics["winning_trades"] = len(winners)
            metrics["losing_trades"] = len(losers)
            metrics["win_rate"] = (
                float(len(winners)) / float(len(closed_positions)) * 100
                if closed_positions else 0.0
            )
            
            # P&L stats
            total_wins = sum(float(p["realized_pnl"]) for p in winners)
            total_losses = abs(sum(float(p["realized_pnl"]) for p in losers))
            
            metrics["avg_win_amount"] = (
                total_wins / len(winners) if winners else 0.0
            )
            metrics["avg_loss_amount"] = (
                total_losses / len(losers) if losers else 0.0
            )
            
            metrics["avg_win_percent"] = (
                sum(float(p["realized_pnl_percent"]) for p in winners) / len(winners)
                if winners else 0.0
            )
            metrics["avg_loss_percent"] = (
                sum(float(p["realized_pnl_percent"]) for p in losers) / len(losers)
                if losers else 0.0
            )
            
            metrics["profit_factor"] = (
                total_wins / total_losses if total_losses > 0 else 0.0
            )
            
            metrics["total_return"] = total_wins - total_losses
            metrics["total_return_percent"] = (
                (metrics["total_return"] / sum(float(p["total_cost"]) for p in closed_positions)) * 100
                if closed_positions else 0.0
            )
            metrics["realized_pnl"] = metrics["total_return"]
            
            # Holding periods
            if closed_positions:
                metrics["avg_holding_period_days"] = (
                    sum(p["holding_period_days"] for p in closed_positions) / len(closed_positions)
                )
                metrics["avg_holding_period_winners"] = (
                    sum(p["holding_period_days"] for p in winners) / len(winners)
                ) if winners else 0.0
                metrics["avg_holding_period_losers"] = (
                    sum(p["holding_period_days"] for p in losers) / len(losers)
                ) if losers else 0.0
            else:
                metrics["avg_holding_period_days"] = 0.0
                metrics["avg_holding_period_winners"] = 0.0
                metrics["avg_holding_period_losers"] = 0.0
            
            # Best/Worst trades
            if closed_positions:
                best = max(closed_positions, key=lambda x: float(x["realized_pnl"]))
                worst = min(closed_positions, key=lambda x: float(x["realized_pnl"]))
                metrics["best_trade"] = self._format_trade_summary(best)
                metrics["worst_trade"] = self._format_trade_summary(worst)
            
            # Current portfolio estimates
            metrics["current_value"] = 0.0  # TODO: Calculate from current holdings
            metrics["total_invested"] = sum(float(p["total_cost"]) for p in closed_positions)
            metrics["unrealized_pnl"] = 0.0  # TODO: Calculate from open positions
            
            # Placeholders for future features
            metrics["annualized_return_percent"] = None
            metrics["sp500_return_percent"] = None
            metrics["alpha"] = None
            metrics["volatility"] = None
            metrics["sharpe_ratio"] = None
            metrics["max_drawdown"] = None
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}", exc_info=True)
            return self._empty_metrics(user_id, period)
        finally:
            db.close()
    
    def _calculate_closed_positions(
        self,
        transactions: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Match buy/sell transactions using FIFO accounting
        Returns list of closed positions with P&L
        """
        # Group by symbol
        by_symbol = {}
        for tx in transactions:
            if tx.symbol not in by_symbol:
                by_symbol[tx.symbol] = []
            by_symbol[tx.symbol].append(tx)
        
        closed_positions = []
        
        for symbol, txs in by_symbol.items():
            # Sort by date
            txs.sort(key=lambda x: x.transaction_date)
            
            # FIFO matching
            buy_queue = []  # List of buys: [{quantity, price, date, tx_id}]
            
            for tx in txs:
                # Extract quantity and price from JSON data
                quantity = Decimal(str(tx.data.get("quantity", 0)))
                price = tx.data.get("price")
                
                if price is None:
                    continue  # Skip transactions without price (e.g., dividends)
                
                price = Decimal(str(price))
                
                if tx.transaction_type == "BUY":
                    buy_queue.append({
                        "quantity": quantity,
                        "price": price,
                        "date": tx.transaction_date,
                        "tx_id": str(tx.id)
                    })
                
                elif tx.transaction_type == "SELL":
                    # SnapTrade returns SELL quantities as negative, take absolute value
                    remaining_to_sell = abs(quantity)
                    sell_price = price
                    sell_date = tx.transaction_date
                    
                    while remaining_to_sell > 0 and buy_queue:
                        buy = buy_queue[0]
                        
                        # Match quantity
                        matched_qty = min(remaining_to_sell, buy["quantity"])
                        
                        # Calculate P&L
                        cost = matched_qty * buy["price"]
                        proceeds = matched_qty * sell_price
                        pnl = proceeds - cost
                        pnl_percent = (pnl / cost) * 100 if cost > 0 else Decimal(0)
                        
                        # Holding period
                        holding_days = (sell_date - buy["date"]).days
                        
                        closed_positions.append({
                            "symbol": symbol,
                            "entry_date": buy["date"],
                            "exit_date": sell_date,
                            "entry_price": buy["price"],
                            "exit_price": sell_price,
                            "quantity": matched_qty,
                            "total_cost": cost,
                            "total_proceeds": proceeds,
                            "realized_pnl": pnl,
                            "realized_pnl_percent": pnl_percent,
                            "holding_period_days": holding_days,
                            "is_winner": pnl > 0
                        })
                        
                        # Update queues
                        remaining_to_sell -= matched_qty
                        buy["quantity"] -= matched_qty
                        
                        if buy["quantity"] <= 0:
                            buy_queue.pop(0)
        
        return closed_positions
    
    def analyze_trading_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Detect behavioral patterns in trading
        Returns list of patterns with recommendations
        """
        try:
            metrics = self.calculate_performance_metrics(user_id)
            
            if metrics.get("total_trades", 0) < 5:
                return []  # Need at least 5 trades to detect patterns
            
            patterns = []
            
            # Pattern: Early exit on winners
            if (metrics.get("avg_holding_period_winners", 0) > 0 and
                metrics.get("avg_holding_period_losers", 0) > 0 and
                metrics["avg_holding_period_winners"] < metrics["avg_holding_period_losers"]):
                patterns.append({
                    "pattern_type": "early_exit_winners",
                    "confidence": 0.85,
                    "description": "You tend to sell winning positions too early",
                    "impact": "negative",
                    "examples": [],
                    "recommendation": f"Consider holding winners longer to maximize gains. Your average winning hold is {metrics['avg_holding_period_winners']:.0f} days vs {metrics['avg_holding_period_losers']:.0f} days for losers."
                })
            
            # Pattern: Low win rate
            if metrics.get("win_rate", 100) < 40:
                patterns.append({
                    "pattern_type": "low_win_rate",
                    "confidence": 0.90,
                    "description": f"Your win rate is {metrics['win_rate']:.0f}% - below average",
                    "impact": "negative",
                    "examples": [],
                    "recommendation": "Focus on high-probability setups and wait for better entry points. Quality over quantity."
                })
            
            # Pattern: High win rate
            elif metrics.get("win_rate", 0) > 65:
                patterns.append({
                    "pattern_type": "high_win_rate",
                    "confidence": 0.90,
                    "description": f"Strong win rate of {metrics['win_rate']:.0f}%",
                    "impact": "positive",
                    "examples": [],
                    "recommendation": "Great job! Keep following your strategy and consider increasing position sizes on high-conviction trades."
                })
            
            # Pattern: Small wins, big losses
            avg_win = metrics.get("avg_win_amount", 0)
            avg_loss = metrics.get("avg_loss_amount", 0)
            if avg_win > 0 and avg_loss > 0 and avg_loss > (avg_win * 1.5):
                patterns.append({
                    "pattern_type": "risk_reward_imbalance",
                    "confidence": 0.85,
                    "description": "Your average loss ($%.2f) is much larger than your average win ($%.2f)" % (avg_loss, avg_win),
                    "impact": "negative",
                    "examples": [],
                    "recommendation": "Use tighter stop losses to protect capital. Aim for at least 2:1 reward-to-risk ratio."
                })
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing trading patterns: {e}", exc_info=True)
            return []
    
    def _get_period_start_date(self, period: str) -> Optional[datetime]:
        """Get start date for a time period"""
        now = datetime.now()
        
        if period == "all_time":
            return None
        elif period == "ytd":
            return datetime(now.year, 1, 1)
        elif period == "1m":
            return now - timedelta(days=30)
        elif period == "3m":
            return now - timedelta(days=90)
        elif period == "6m":
            return now - timedelta(days=180)
        elif period == "1y":
            return now - timedelta(days=365)
        
        return None
    
    def _empty_metrics(self, user_id: str, period: str) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            "user_id": user_id,
            "period": period,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_return": 0.0,
            "total_return_percent": 0.0,
            "avg_win_amount": 0.0,
            "avg_loss_amount": 0.0,
            "avg_win_percent": 0.0,
            "avg_loss_percent": 0.0,
            "profit_factor": 0.0,
            "avg_holding_period_days": 0.0,
            "avg_holding_period_winners": 0.0,
            "avg_holding_period_losers": 0.0,
            "current_value": 0.0,
            "total_invested": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "calculated_at": datetime.now().isoformat()
        }
    
    def _format_trade_summary(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Format a trade for display"""
        return {
            "symbol": trade["symbol"],
            "entry_date": trade["entry_date"].isoformat() if isinstance(trade["entry_date"], datetime) else trade["entry_date"],
            "exit_date": trade["exit_date"].isoformat() if isinstance(trade["exit_date"], datetime) else trade["exit_date"],
            "entry_price": float(trade["entry_price"]),
            "exit_price": float(trade["exit_price"]),
            "quantity": float(trade["quantity"]),
            "realized_pnl": float(trade["realized_pnl"]),
            "realized_pnl_percent": float(trade["realized_pnl_percent"]),
            "holding_period_days": trade["holding_period_days"]
        }


# Global instance
analytics_service = AnalyticsService()


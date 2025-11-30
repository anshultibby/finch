"""
Strategy Backtesting Engine - Test strategies on historical data
"""
import logging
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from backend.models.strategy import (
    TradingStrategy, StrategyBacktest, BacktestTrade, 
    Condition, DataRequirement
)
from backend.modules.tools.fmp_client import FMPClient

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Engine to backtest trading strategies on historical data"""
    
    def __init__(self, fmp_client: FMPClient):
        self.fmp = fmp_client
        
    async def run_backtest(
        self,
        strategy: TradingStrategy,
        start_date: date,
        end_date: date,
        initial_capital: float = 100000,
        universe: Optional[List[str]] = None
    ) -> StrategyBacktest:
        """
        Backtest a strategy on historical data
        
        Args:
            strategy: Strategy to test
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Starting capital
            universe: List of tickers to test on (defaults to S&P 500)
            
        Returns:
            StrategyBacktest with complete results
        """
        logger.info(f"Running backtest for strategy '{strategy.name}' from {start_date} to {end_date}")
        
        # Get stock universe
        if universe is None:
            universe = await self._get_sp500_tickers()
        
        logger.info(f"Testing on {len(universe)} stocks")
        
        # Initialize tracking
        positions = {}  # {ticker: position_info}
        trades = []
        cash = initial_capital
        equity_curve = []
        
        # Pre-fetch all historical data for universe
        logger.info("Fetching historical data...")
        historical_data = await self._fetch_historical_data_bulk(
            universe, 
            start_date, 
            end_date,
            strategy.data_requirements
        )
        
        # Get all trading days
        trading_days = self._get_trading_days(start_date, end_date)
        
        logger.info(f"Simulating {len(trading_days)} trading days...")
        
        # Iterate through each trading day
        for current_date in trading_days:
            daily_data = {}
            
            # Get data for this date for all stocks
            for ticker in universe:
                if ticker in historical_data and current_date in historical_data[ticker]:
                    daily_data[ticker] = historical_data[ticker][current_date]
            
            # Check exit conditions for existing positions
            for ticker in list(positions.keys()):
                if ticker not in daily_data:
                    continue
                    
                position = positions[ticker]
                current_price = daily_data[ticker].get('price', daily_data[ticker].get('close', 0))
                
                # Evaluate exit conditions
                should_exit, exit_reason = self._should_exit(
                    strategy,
                    daily_data[ticker],
                    position,
                    current_date
                )
                
                if should_exit and current_price > 0:
                    # Exit position
                    exit_value = position['shares'] * current_price
                    pnl = exit_value - position['cost_basis']
                    pnl_pct = (current_price / position['entry_price'] - 1) * 100
                    days_held = (current_date - position['entry_date']).days
                    
                    trades.append(BacktestTrade(
                        ticker=ticker,
                        entry_date=position['entry_date'],
                        entry_price=position['entry_price'],
                        exit_date=current_date,
                        exit_price=current_price,
                        shares=position['shares'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        days_held=days_held,
                        exit_reason=exit_reason
                    ))
                    
                    cash += exit_value
                    del positions[ticker]
                    
                    logger.debug(f"Exited {ticker}: {pnl_pct:.2f}% in {days_held} days ({exit_reason})")
            
            # Check entry conditions for new positions
            if len(positions) < strategy.risk_parameters.max_positions:
                for ticker in universe:
                    if ticker in positions or ticker not in daily_data:
                        continue
                    
                    if self._should_enter(strategy, daily_data[ticker]) and cash > 0:
                        current_price = daily_data[ticker].get('price', daily_data[ticker].get('close', 0))
                        
                        if current_price <= 0:
                            continue
                        
                        # Calculate position size
                        position_value = initial_capital * (strategy.risk_parameters.position_size_pct / 100)
                        shares = int(position_value / current_price)
                        cost = shares * current_price
                        
                        if cost <= cash and shares > 0:
                            positions[ticker] = {
                                'entry_date': current_date,
                                'entry_price': current_price,
                                'shares': shares,
                                'cost_basis': cost
                            }
                            cash -= cost
                            
                            logger.debug(f"Entered {ticker} at ${current_price:.2f}, {shares} shares")
                            
                            # Only take max_positions at a time
                            if len(positions) >= strategy.risk_parameters.max_positions:
                                break
            
            # Calculate total equity
            total_position_value = 0
            for ticker, position in positions.items():
                if ticker in daily_data:
                    current_price = daily_data[ticker].get('price', daily_data[ticker].get('close', 0))
                    total_position_value += position['shares'] * current_price
            
            total_equity = cash + total_position_value
            
            equity_curve.append({
                'date': current_date.isoformat(),
                'equity': round(total_equity, 2),
                'cash': round(cash, 2),
                'positions_value': round(total_position_value, 2),
                'num_positions': len(positions)
            })
        
        # Close any remaining positions at end date
        for ticker, position in positions.items():
            # Use last known price or entry price
            exit_price = position['entry_price']
            if ticker in historical_data and end_date in historical_data[ticker]:
                exit_price = historical_data[ticker][end_date].get('price', exit_price)
            
            exit_value = position['shares'] * exit_price
            pnl = exit_value - position['cost_basis']
            pnl_pct = (exit_price / position['entry_price'] - 1) * 100
            days_held = (end_date - position['entry_date']).days
            
            trades.append(BacktestTrade(
                ticker=ticker,
                entry_date=position['entry_date'],
                entry_price=position['entry_price'],
                exit_date=end_date,
                exit_price=exit_price,
                shares=position['shares'],
                pnl=pnl,
                pnl_pct=pnl_pct,
                days_held=days_held,
                exit_reason='backtest_end'
            ))
        
        # Calculate performance metrics
        metrics = self._calculate_metrics(trades, equity_curve, initial_capital)
        
        # Find best and worst trades
        best_trade = max(trades, key=lambda t: t.pnl) if trades else None
        worst_trade = min(trades, key=lambda t: t.pnl) if trades else None
        
        logger.info(f"Backtest complete: {len(trades)} trades, {metrics['win_rate']:.1f}% win rate, {metrics['total_return_pct']:.2f}% return")
        
        return StrategyBacktest(
            strategy_id=strategy.id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            best_trade=best_trade,
            worst_trade=worst_trade,
            trades=trades,
            equity_curve=equity_curve,
            **metrics
        )
    
    def _should_enter(self, strategy: TradingStrategy, data: Dict[str, Any]) -> bool:
        """Evaluate if entry conditions are met"""
        return self._evaluate_conditions(
            strategy.entry_conditions,
            data,
            strategy.entry_logic
        )
    
    def _should_exit(
        self,
        strategy: TradingStrategy,
        data: Dict[str, Any],
        position: Dict[str, Any],
        current_date: date
    ) -> tuple[bool, str]:
        """
        Evaluate if exit conditions are met
        
        Returns:
            (should_exit, exit_reason)
        """
        current_price = data.get('price', data.get('close', 0))
        
        if current_price <= 0:
            return False, ""
        
        # Check risk parameters first
        pnl_pct = (current_price / position['entry_price'] - 1) * 100
        days_held = (current_date - position['entry_date']).days
        
        # Stop loss
        if strategy.risk_parameters.stop_loss_pct:
            if pnl_pct <= -strategy.risk_parameters.stop_loss_pct:
                return True, "stop_loss"
        
        # Take profit
        if strategy.risk_parameters.take_profit_pct:
            if pnl_pct >= strategy.risk_parameters.take_profit_pct:
                return True, "take_profit"
        
        # Max hold time
        if strategy.risk_parameters.max_hold_days:
            if days_held >= strategy.risk_parameters.max_hold_days:
                return True, "max_hold"
        
        # Check exit signal conditions
        if self._evaluate_conditions(strategy.exit_conditions, data, strategy.exit_logic):
            return True, "signal"
        
        return False, ""
    
    def _evaluate_conditions(
        self,
        conditions: List[Condition],
        data: Dict[str, Any],
        logic: str
    ) -> bool:
        """Evaluate if conditions are met given data"""
        if not conditions:
            return False
        
        results = []
        
        for condition in conditions:
            field_value = data.get(condition.field)
            
            if field_value is None:
                results.append(False)
                continue
            
            result = False
            
            if condition.operator == "gt":
                result = field_value > condition.value
            elif condition.operator == "lt":
                result = field_value < condition.value
            elif condition.operator == "gte":
                result = field_value >= condition.value
            elif condition.operator == "lte":
                result = field_value <= condition.value
            elif condition.operator == "eq":
                result = field_value == condition.value
            elif condition.operator == "between":
                if isinstance(condition.value, list) and len(condition.value) == 2:
                    result = condition.value[0] <= field_value <= condition.value[1]
            elif condition.operator == "in":
                if isinstance(condition.value, list):
                    result = field_value in condition.value
            
            results.append(result)
        
        if logic == "AND":
            return all(results)
        else:  # OR
            return any(results)
    
    def _calculate_metrics(
        self,
        trades: List[BacktestTrade],
        equity_curve: List[Dict[str, Any]],
        initial_capital: float
    ) -> Dict[str, Any]:
        """Calculate strategy performance metrics"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return_pct': 0,
                'total_return_dollars': 0,
                'final_equity': initial_capital,
                'avg_win_pct': 0,
                'avg_loss_pct': 0,
                'profit_factor': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': None
            }
        
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl < 0]
        
        final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
        
        # Calculate max drawdown
        peak = initial_capital
        max_dd = 0
        for point in equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Calculate Sharpe ratio (simplified daily returns)
        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i-1]['equity']
            curr_equity = equity_curve[i]['equity']
            if prev_equity > 0:
                daily_return = (curr_equity / prev_equity) - 1
                returns.append(daily_return)
        
        sharpe = None
        if returns and len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                sharpe = round((avg_return / std_return) * np.sqrt(252), 2)
        
        # Calculate profit factor
        total_wins = sum(t.pnl for t in wins)
        total_losses = abs(sum(t.pnl for t in losses))
        profit_factor = round(total_wins / total_losses, 2) if total_losses > 0 else 99.99
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': round(len(wins) / len(trades) * 100, 2) if trades else 0,
            'total_return_pct': round((final_equity / initial_capital - 1) * 100, 2),
            'total_return_dollars': round(final_equity - initial_capital, 2),
            'final_equity': round(final_equity, 2),
            'avg_win_pct': round(np.mean([t.pnl_pct for t in wins]), 2) if wins else 0,
            'avg_loss_pct': round(np.mean([t.pnl_pct for t in losses]), 2) if losses else 0,
            'profit_factor': profit_factor,
            'max_drawdown_pct': round(max_dd, 2),
            'sharpe_ratio': sharpe
        }
    
    async def _fetch_historical_data_bulk(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        data_requirements: List[DataRequirement]
    ) -> Dict[str, Dict[date, Dict[str, Any]]]:
        """
        Fetch all required historical data for all tickers
        
        Returns nested dict: {ticker: {date: {field: value}}}
        """
        all_data = {}
        
        for ticker in tickers:
            try:
                ticker_data = await self._fetch_ticker_historical_data(
                    ticker,
                    start_date,
                    end_date,
                    data_requirements
                )
                all_data[ticker] = ticker_data
            except Exception as e:
                logger.warning(f"Failed to fetch data for {ticker}: {e}")
                continue
        
        return all_data
    
    async def _fetch_ticker_historical_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        data_requirements: List[DataRequirement]
    ) -> Dict[date, Dict[str, Any]]:
        """Fetch all required data for a single ticker"""
        # Initialize data structure
        data_by_date = defaultdict(dict)
        
        # Fetch price history (needed for most strategies)
        try:
            price_data = await self.fmp.get_historical_price(ticker, start_date, end_date)
            if price_data:
                for bar in price_data:
                    bar_date = datetime.strptime(bar['date'], '%Y-%m-%d').date()
                    data_by_date[bar_date].update({
                        'price': bar['close'],
                        'close': bar['close'],
                        'open': bar['open'],
                        'high': bar['high'],
                        'low': bar['low'],
                        'volume': bar['volume']
                    })
        except Exception as e:
            logger.debug(f"No price data for {ticker}: {e}")
            return {}
        
        # Calculate indicators based on requirements
        for req in data_requirements:
            if req.source == "calculated":
                await self._calculate_indicator(ticker, data_by_date, req)
            elif req.source == "fmp":
                await self._fetch_fmp_data(ticker, data_by_date, req, start_date, end_date)
        
        return dict(data_by_date)
    
    async def _calculate_indicator(
        self,
        ticker: str,
        data_by_date: Dict[date, Dict[str, Any]],
        requirement: DataRequirement
    ):
        """Calculate technical indicators"""
        indicator_type = requirement.data_type
        params = requirement.parameters
        
        # Get sorted dates and prices
        sorted_dates = sorted(data_by_date.keys())
        closes = [data_by_date[d]['close'] for d in sorted_dates]
        
        if indicator_type == "rsi":
            period = params.get('period', 14)
            rsi_values = self._calculate_rsi(closes, period)
            for i, d in enumerate(sorted_dates):
                if i < period:
                    continue
                data_by_date[d]['rsi'] = round(rsi_values[i], 2)
        
        elif indicator_type == "moving_average" or indicator_type.startswith("sma"):
            period = params.get('period', 20)
            ma_values = self._calculate_sma(closes, period)
            for i, d in enumerate(sorted_dates):
                if i < period - 1:
                    continue
                data_by_date[d][f'sma_{period}'] = round(ma_values[i], 2)
        
        elif indicator_type == "volume_avg":
            period = params.get('period', 20)
            volumes = [data_by_date[d].get('volume', 0) for d in sorted_dates]
            vol_avg = self._calculate_sma(volumes, period)
            for i, d in enumerate(sorted_dates):
                if i < period - 1:
                    continue
                data_by_date[d]['volume_avg'] = int(vol_avg[i])
    
    async def _fetch_fmp_data(
        self,
        ticker: str,
        data_by_date: Dict[date, Dict[str, Any]],
        requirement: DataRequirement,
        start_date: date,
        end_date: date
    ):
        """Fetch FMP-specific data like insider trades"""
        if requirement.data_type == "insider_trading":
            try:
                # Fetch insider trades
                insider_data = await self.fmp.get_insider_trades(ticker)
                
                # Count buys/sells in rolling window for each date
                days = requirement.parameters.get('days', 30)
                
                for current_date in sorted(data_by_date.keys()):
                    window_start = current_date - timedelta(days=days)
                    
                    buy_count = 0
                    sell_count = 0
                    buy_amount = 0
                    sell_amount = 0
                    
                    for trade in insider_data:
                        trade_date = datetime.strptime(trade['transactionDate'], '%Y-%m-%d').date()
                        if window_start <= trade_date <= current_date:
                            if trade['transactionType'] == 'P-Purchase':
                                buy_count += 1
                                buy_amount += trade.get('securitiesTransacted', 0) * trade.get('price', 0)
                            elif trade['transactionType'] == 'S-Sale':
                                sell_count += 1
                                sell_amount += trade.get('securitiesTransacted', 0) * trade.get('price', 0)
                    
                    data_by_date[current_date]['insider_buy_count'] = buy_count
                    data_by_date[current_date]['insider_sell_count'] = sell_count
                    data_by_date[current_date]['insider_buy_amount'] = buy_amount
                    data_by_date[current_date]['insider_sell_amount'] = sell_amount
            except Exception as e:
                logger.debug(f"No insider data for {ticker}: {e}")
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate RSI indicator"""
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        rsi = np.zeros_like(prices)
        rsi[:period] = 50  # Default for initial period
        
        for i in range(period, len(prices)):
            delta = deltas[i - 1]
            if delta > 0:
                upval = delta
                downval = 0
            else:
                upval = 0
                downval = -delta
            
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            
            rs = up / down if down != 0 else 100
            rsi[i] = 100 - (100 / (1 + rs))
        
        return rsi.tolist()
    
    def _calculate_sma(self, values: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        sma = []
        for i in range(len(values)):
            if i < period - 1:
                sma.append(0)
            else:
                sma.append(sum(values[i - period + 1:i + 1]) / period)
        return sma
    
    def _get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Get list of trading days (excluding weekends)"""
        trading_days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                trading_days.append(current)
            current += timedelta(days=1)
        return trading_days
    
    async def _get_sp500_tickers(self) -> List[str]:
        """Get S&P 500 ticker list"""
        # For MVP, return a subset of major tickers
        # In production, fetch from FMP or another source
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B',
            'UNH', 'JNJ', 'JPM', 'V', 'PG', 'XOM', 'HD', 'CVX', 'MA', 'ABBV',
            'PFE', 'COST', 'AVGO', 'KO', 'PEP', 'MRK', 'TMO', 'CSCO', 'ACN',
            'NKE', 'DIS', 'ABT', 'WMT', 'CRM', 'ADBE', 'VZ', 'NFLX', 'CMCSA',
            'INTC', 'AMD', 'QCOM', 'TXN', 'HON', 'UNP', 'UPS', 'AMGN', 'RTX',
            'LOW', 'ORCL', 'BA', 'IBM', 'SPGI'
        ]


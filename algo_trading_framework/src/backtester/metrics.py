import numpy as np
import pandas as pd
from typing import List, Dict, Any
try:
    from algo_trading_framework.src.core.models import Trade
except ImportError:
    class Trade: pass # Dummy for standalone use

def calculate_total_return(initial_capital: float, final_portfolio_value: float) -> float:
    """Calculates the total return as a percentage."""
    if initial_capital == 0: return 0.0
    return ((final_portfolio_value - initial_capital) / initial_capital) * 100

def calculate_sharpe_ratio(returns_series: pd.Series, risk_free_rate_annual: float = 0.0, periods_per_year: int = 252) -> float:
    """
    Calculates a simplified Sharpe Ratio.
    Args:
        returns_series (pd.Series): Series of periodic returns (e.g., daily).
        risk_free_rate_annual (float): Annual risk-free rate.
        periods_per_year (int): Number of trading periods in a year (e.g., 252 for daily).
    Returns:
        float: Sharpe Ratio.
    """
    if returns_series.empty or returns_series.std() == 0:
        return 0.0
    
    excess_returns = returns_series - (risk_free_rate_annual / periods_per_year)
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(periods_per_year) if excess_returns.std() != 0 else 0.0

def calculate_max_drawdown(portfolio_values: pd.Series) -> float:
    """
    Calculates the maximum drawdown from a series of portfolio values.
    Returns the drawdown as a positive percentage (e.g., 20.0 for a 20% drawdown).
    """
    if portfolio_values.empty:
        return 0.0
    
    cumulative_max = portfolio_values.cummax()
    drawdown = (portfolio_values - cumulative_max) / cumulative_max
    max_drawdown_pct = abs(drawdown.min()) * 100
    return max_drawdown_pct if not pd.isna(max_drawdown_pct) else 0.0

def calculate_win_loss_ratio(trades: List[Trade]) -> float:
    """Calculates the win/loss ratio from a list of trades."""
    wins = sum(1 for trade in trades if trade.price * (1 if trade.trade_type == "BUY" else -1) > 0) # Simplified: assumes PnL > 0 for win
    # This is a very naive PnL for individual trades. A proper Trade object should have realized PnL.
    # For now, let's assume a trade is a "win" if it's a buy and price > 0 (placeholder) or sell and price < 0 (placeholder)
    # A more realistic approach requires comparing entry and exit prices for closed trades.
    # Given the current Trade model, we can't easily calculate individual trade P&L without knowing context.
    # This function will need to be improved once P&L is tracked per trade or per closed position.
    
    # Placeholder: Let's assume a trade object will eventually have a 'pnl' attribute.
    # For now, this metric will be very basic and likely not very useful.
    # wins = sum(1 for trade in trades if hasattr(trade, 'pnl') and trade.pnl > 0)
    # losses = sum(1 for trade in trades if hasattr(trade, 'pnl') and trade.pnl < 0)
    
    # Using a proxy for now: count buy trades vs sell trades if no PnL available
    # This is NOT a win/loss ratio. It's just a placeholder.
    # A real win/loss ratio needs realized PnL per trade.
    # The BacktestEngine will need to generate trades with PnL.
    
    # Let's assume the BacktestEngine will populate a 'pnl' field in the Trade objects it logs.
    profitable_trades = sum(1 for trade in trades if hasattr(trade, 'pnl') and trade.pnl > 0)
    losing_trades = sum(1 for trade in trades if hasattr(trade, 'pnl') and trade.pnl < 0)

    if losing_trades == 0:
        return float('inf') if profitable_trades > 0 else 0.0 # Avoid division by zero
    return profitable_trades / losing_trades

def calculate_sortino_ratio(returns_series: pd.Series, risk_free_rate_annual: float = 0.0, periods_per_year: int = 252, target_return_annual: float = 0.0) -> float:
    """
    Calculates the Sortino Ratio.
    Args:
        returns_series (pd.Series): Series of periodic returns.
        risk_free_rate_annual (float): Annual risk-free rate.
        periods_per_year (int): Number of trading periods in a year.
        target_return_annual (float): Annual target return, often the risk-free rate.
    Returns:
        float: Sortino Ratio.
    """
    if returns_series.empty:
        return 0.0

    target_return_periodic = (target_return_annual + risk_free_rate_annual) / periods_per_year # Adjust target by RFR
    
    downside_returns = returns_series[returns_series < target_return_periodic]
    downside_deviation = downside_returns.std()
    
    if pd.isna(downside_deviation) or downside_deviation == 0:
        return float('inf') if returns_series.mean() > target_return_periodic else 0.0

    expected_return = returns_series.mean()
    return (expected_return - (risk_free_rate_annual / periods_per_year)) / downside_deviation * np.sqrt(periods_per_year)


def get_performance_summary(portfolio_history: pd.DataFrame, trades: List[Trade], initial_capital: float) -> Dict[str, Any]:
    """
    Generates a dictionary of overall performance metrics.
    Args:
        portfolio_history (pd.DataFrame): DataFrame with 'timestamp' and 'portfolio_value' columns.
        trades (List[Trade]): List of all executed Trade objects. (Assumes Trade object has 'pnl' attribute)
        initial_capital (float): The starting capital.
    Returns:
        Dict[str, Any]: A dictionary containing key performance indicators.
    """
    if portfolio_history.empty:
        return {"error": "Portfolio history is empty."}

    final_value = portfolio_history['portfolio_value'].iloc[-1]
    
    # Calculate daily returns if portfolio_history has daily values
    # For simplicity, if we only have portfolio_value at each step, we can calculate periodic returns
    portfolio_returns = portfolio_history['portfolio_value'].pct_change().dropna()

    summary = {
        "Initial Capital": initial_capital,
        "Final Portfolio Value": final_value,
        "Total Return (%)": calculate_total_return(initial_capital, final_value),
        "Max Drawdown (%)": calculate_max_drawdown(portfolio_history['portfolio_value']),
        "Sharpe Ratio (Annualized, Rf=0%)": calculate_sharpe_ratio(portfolio_returns),
        "Sortino Ratio (Annualized, Rf=0%, Target=0%)": calculate_sortino_ratio(portfolio_returns),
        "Total Trades": len(trades),
        # "Win/Loss Ratio": calculate_win_loss_ratio(trades), # This needs trades with PnL
    }
    
    # Add win/loss ratio if trades have PnL (improvement for later)
    if trades and hasattr(trades[0], 'pnl'):
        summary["Win/Loss Ratio"] = calculate_win_loss_ratio(trades)
    else:
        summary["Win/Loss Ratio"] = "N/A (Trade PnL not available)"
        
    return summary

```

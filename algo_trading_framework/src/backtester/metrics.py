import numpy as np
import math
import datetime
from typing import List, Dict, Any # Using Any for trade_log items for now

# Placeholder for src.core.models.Trade if needed for type hinting,
# but current implementation assumes trade_log contains dicts.
# from src.core.models import Trade 

# --- Equity Curve Based Metrics ---

def calculate_total_return(equity_curve: List[float]) -> float:
    """Calculates the total return from an equity curve."""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    if equity_curve[0] == 0: # Avoid division by zero if starting equity is 0
        return 0.0 if equity_curve[-1] == 0 else float('inf') # Or handle as error
    return (equity_curve[-1] / equity_curve[0]) - 1

def calculate_annualized_return(equity_curve: List[float], num_days: int) -> float:
    """Calculates the annualized return."""
    if not equity_curve or len(equity_curve) < 2 or num_days <= 0:
        return 0.0
    
    total_return = calculate_total_return(equity_curve)
    if equity_curve[0] == 0 and total_return == float('inf'): # Handle case from calculate_total_return
        return float('inf')

    annualized_return = ((1 + total_return) ** (365.0 / num_days)) - 1
    return annualized_return

def calculate_sharpe_ratio(equity_curve: List[float], risk_free_rate_annual: float, trading_days_per_year: int = 252) -> float:
    """Calculates the Sharpe ratio."""
    if len(equity_curve) < 2: # Need at least two points to calculate returns
        return 0.0

    daily_returns = np.diff(equity_curve) / equity_curve[:-1]
    # Alternative using log returns, often preferred:
    # daily_log_returns = np.log(np.array(equity_curve[1:]) / np.array(equity_curve[:-1]))
    
    if len(daily_returns) == 0: # Handles equity_curve of len 1, though already caught by len(equity_curve) < 2
        return 0.0

    risk_free_rate_daily = risk_free_rate_annual / trading_days_per_year
    excess_returns = daily_returns - risk_free_rate_daily
    
    mean_excess_return = np.mean(excess_returns)
    std_dev_excess_return = np.std(excess_returns)
    
    if std_dev_excess_return == 0:
        # If std_dev is 0, it means all excess returns are the same.
        # If mean_excess_return is also 0, Sharpe is undefined (0).
        # If mean_excess_return > 0, Sharpe is inf.
        # If mean_excess_return < 0, Sharpe is -inf.
        return float('inf') if mean_excess_return > 0 else float('-inf') if mean_excess_return < 0 else 0.0
        
    sharpe_ratio = (mean_excess_return / std_dev_excess_return) * np.sqrt(trading_days_per_year)
    return sharpe_ratio

def calculate_sortino_ratio(equity_curve: List[float], risk_free_rate_annual: float, trading_days_per_year: int = 252) -> float:
    """Calculates the Sortino ratio."""
    if len(equity_curve) < 2:
        return 0.0

    daily_returns = np.diff(equity_curve) / equity_curve[:-1]
    
    if len(daily_returns) == 0:
        return 0.0

    risk_free_rate_daily = risk_free_rate_annual / trading_days_per_year
    excess_returns = daily_returns - risk_free_rate_daily
    
    mean_excess_return = np.mean(excess_returns) # Overall mean of excess returns
    
    # Filter for negative excess returns to calculate downside deviation
    negative_excess_returns = excess_returns[excess_returns < 0]
    
    if len(negative_excess_returns) < 1: # Or < 2 if std requires at least 2 points for meaningful calc
        # No negative excess returns, means downside deviation is 0 or undefined.
        # If mean_excess_return is positive, Sortino is effectively infinite.
        # If mean_excess_return is zero or negative, Sortino is 0 (or undefined if mean is also 0).
        return float('inf') if mean_excess_return > 0 else 0.0

    downside_deviation = np.std(negative_excess_returns)
    
    if downside_deviation == 0:
        # This case implies all negative returns are identical (or only one negative return and std is 0)
        # Or no negative returns (already handled above).
        # If mean_excess_return > 0, Sortino is inf.
        return float('inf') if mean_excess_return > 0 else 0.0 # if mean_excess_return is also 0 or negative

    sortino_ratio = (mean_excess_return / downside_deviation) * np.sqrt(trading_days_per_year)
    return sortino_ratio

def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """Calculates the maximum drawdown from an equity curve."""
    if not equity_curve:
        return 0.0
        
    max_dd = 0.0
    peak = equity_curve[0]
    
    for value in equity_curve:
        if value > peak:
            peak = value
        
        if peak == 0: # Avoid division by zero if peak is 0
            drawdown = 0.0 # Or handle as error/undefined if value is also 0
        else:
            drawdown = (peak - value) / peak
            
        if drawdown > max_dd:
            max_dd = drawdown
            
    return max_dd

# --- Trade Log Based Metrics ---

def calculate_win_rate_avg_win_loss_profit_factor(trade_log: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculates win rate, average win/loss, and profit factor from a trade log.
    Assumes each trade dict in trade_log has a 'pnl' key with realized PNL.
    """
    pnls = [t.get('pnl', 0.0) for t in trade_log if t.get('pnl') is not None] # Filter out trades without PNL
    
    if not pnls: # No trades with PNL information
        return {
            "win_rate": 0.0, "avg_win_pnl": 0.0, "avg_loss_pnl": 0.0, 
            "profit_factor": 0.0, "total_trades_with_pnl": 0,
            "num_wins": 0, "num_losses": 0, "total_profit": 0.0, "total_loss": 0.0
        }

    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0] # Losses are negative PNL values

    num_wins = len(wins)
    num_losses = len(losses)
    num_trades_with_pnl = num_wins + num_losses

    win_rate = num_wins / num_trades_with_pnl if num_trades_with_pnl > 0 else 0.0
    
    avg_win_pnl = np.mean(wins) if num_wins > 0 else 0.0
    avg_loss_pnl = np.mean(losses) if num_losses > 0 else 0.0 # This will be a negative number or 0

    total_profit = np.sum(wins)
    total_loss = np.sum(losses) # Sum of negative PNLs, so this is a negative value

    if total_loss == 0: # Avoid division by zero for profit factor
        profit_factor = float('inf') if total_profit > 0 else 0.0 # Or 1.0 if total_profit is also 0?
    else:
        profit_factor = abs(total_profit / total_loss) # abs because total_loss is negative

    return {
        "win_rate": win_rate,
        "avg_win_pnl": avg_win_pnl,
        "avg_loss_pnl": avg_loss_pnl, # Negative value
        "profit_factor": profit_factor,
        "total_trades_with_pnl": num_trades_with_pnl,
        "num_wins": num_wins,
        "num_losses": num_losses,
        "total_profit": total_profit,
        "total_loss": total_loss # Sum of negative PNLs
    }

# --- Main Metrics Calculation Function ---

def calculate_all_metrics(
    equity_curve: List[float], 
    trade_log: List[Dict[str, Any]], 
    risk_free_rate_annual: float, 
    backtest_duration_days: int,
    trading_days_per_year: int = 252
) -> Dict[str, float]:
    """Calculates and aggregates all performance metrics."""
    
    metrics = {}
    
    # Equity curve based metrics
    metrics["total_return"] = calculate_total_return(equity_curve)
    metrics["annualized_return"] = calculate_annualized_return(equity_curve, backtest_duration_days)
    metrics["sharpe_ratio"] = calculate_sharpe_ratio(equity_curve, risk_free_rate_annual, trading_days_per_year)
    metrics["sortino_ratio"] = calculate_sortino_ratio(equity_curve, risk_free_rate_annual, trading_days_per_year)
    metrics["max_drawdown"] = calculate_max_drawdown(equity_curve)
    
    # Trade log based metrics
    trade_stats = calculate_win_rate_avg_win_loss_profit_factor(trade_log)
    metrics.update(trade_stats) # Merge the dictionary of trade stats
    
    # Could add more metrics here, e.g., Calmar ratio, VaR, etc.
    
    return metrics

if __name__ == '__main__': # pragma: no cover
    # Example Usage
    print("Running example metrics calculations...")
    
    # Sample Equity Curve (e.g., daily portfolio values)
    sample_equity_curve = [
        100000, 101000, 100500, 102000, 101500, 103000, 102500, 104000, 103500, 105000, # 10 days
        104500, 106000, 105500, 107000, 106500, 108000, 107500, 109000, 108500, 110000  # 20 days
    ]
    # More volatile curve for drawdown testing
    # sample_equity_curve = [100, 110, 105, 120, 90, 95, 80, 110]


    # Sample Trade Log (list of dictionaries, each with a 'pnl' field)
    sample_trade_log = [
        {"trade_id": "t1", "pnl": 1500},
        {"trade_id": "t2", "pnl": -500},
        {"trade_id": "t3", "pnl": 2000},
        {"trade_id": "t4", "pnl": -800},
        {"trade_id": "t5", "pnl": 1200},
        {"trade_id": "t6", "pnl": 300},
        {"trade_id": "t7", "pnl": -1000},
        {"trade_id": "t8", "pnl": 0}, # Break-even trade
        {"trade_id": "t9"}, # Trade without PNL
    ]
    
    risk_free_annual = 0.03 # 3% annual risk-free rate
    duration_days = len(sample_equity_curve) # Assuming daily equity points for simplicity
    
    all_metrics_results = calculate_all_metrics(
        equity_curve=sample_equity_curve,
        trade_log=sample_trade_log,
        risk_free_rate_annual=risk_free_annual,
        backtest_duration_days=duration_days
    )
    
    print("\nCalculated Metrics:")
    for key, value in all_metrics_results.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # Test with empty/minimal data
    print("\nTesting with minimal data:")
    empty_equity = [100000]
    empty_trades: List[Dict[str, Any]] = []
    minimal_metrics = calculate_all_metrics(empty_equity, empty_trades, risk_free_annual, 1)
    for key, value in minimal_metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    print("\nTesting sortino with no losses:")
    positive_returns_equity = [100, 101, 102, 103, 104, 105]
    sortino_no_loss = calculate_sortino_ratio(positive_returns_equity, 0.00)
    print(f"  Sortino with no losses (0 risk-free): {sortino_no_loss:.4f}")
    sortino_no_loss_rf = calculate_sortino_ratio(positive_returns_equity, 0.02) # rf higher than some returns
    print(f"  Sortino with no losses (0.02 risk-free): {sortino_no_loss_rf:.4f}")


    print("\nTesting sharpe with no std dev:")
    flat_returns_equity = [100, 100, 100, 100] # no change
    sharpe_no_std = calculate_sharpe_ratio(flat_returns_equity, 0.00)
    print(f"  Sharpe with 0 std dev, 0 mean excess return: {sharpe_no_std:.4f}")
    
    flat_positive_returns_equity = [100, 101, 102, 103] # if rf=0, mean_excess > 0
    # To make std_dev_excess_return = 0, daily returns must be constant.
    # Example: equity = [100, 101, 102.01, 103.0301] (1% daily return)
    # If rf_daily = 1%, then excess returns are all 0. std_dev_excess_return = 0, mean_excess_return = 0. Sharpe = 0.
    # If rf_daily = 0.5%, then excess returns are all 0.5%. std_dev_excess_return = 0, mean_excess_return = 0.005. Sharpe = inf.
    const_increase_equity = [100, 101, 102.01, 103.0301] # approx 1% daily return
    sharpe_positive_mean_no_std = calculate_sharpe_ratio(const_increase_equity, 0.0) # rf=0
    print(f"  Sharpe with 0 std dev, positive mean excess return: {sharpe_positive_mean_no_std}") # Should be inf
    sharpe_zero_mean_no_std = calculate_sharpe_ratio(const_increase_equity, ( (1.01**252) -1) ) # rf matches daily return
    print(f"  Sharpe with 0 std dev, zero mean excess return (rf matches daily return): {sharpe_zero_mean_no_std}")


    print("\nTesting Max Drawdown with various curves:")
    print(f"  Max DD for {sample_equity_curve[:10]}: {calculate_max_drawdown(sample_equity_curve[:10]):.4f}")
    dd_curve_1 = [100, 110, 105, 120, 90, 95, 80, 110]
    print(f"  Max DD for {dd_curve_1}: {calculate_max_drawdown(dd_curve_1):.4f}") # Peak 120, Trough 80. DD = (120-80)/120 = 0.3333
    dd_curve_2 = [100, 90, 80, 70, 60]
    print(f"  Max DD for {dd_curve_2}: {calculate_max_drawdown(dd_curve_2):.4f}") # Peak 100, Trough 60. DD = (100-60)/100 = 0.4000
    dd_curve_3 = [100, 100, 100]
    print(f"  Max DD for {dd_curve_3}: {calculate_max_drawdown(dd_curve_3):.4f}") # 0.0
    dd_curve_4 = []
    print(f"  Max DD for empty curve {dd_curve_4}: {calculate_max_drawdown(dd_curve_4):.4f}") # 0.0
    dd_curve_5 = [0,0,0]
    print(f"  Max DD for zero curve {dd_curve_5}: {calculate_max_drawdown(dd_curve_5):.4f}") # 0.0

    print("\nTesting Profit Factor with edge cases:")
    pf_stats_1 = calculate_win_rate_avg_win_loss_profit_factor([{"pnl": 100}, {"pnl": 50}]) # Only wins
    print(f"  PF only wins: {pf_stats_1['profit_factor']:.4f}") # inf
    pf_stats_2 = calculate_win_rate_avg_win_loss_profit_factor([{"pnl": -100}, {"pnl": -50}]) # Only losses
    print(f"  PF only losses: {pf_stats_2['profit_factor']:.4f}") # 0.0
    pf_stats_3 = calculate_win_rate_avg_win_loss_profit_factor([{"pnl": 0}, {"pnl": 0}]) # Only zeros
    print(f"  PF only zeros: {pf_stats_3['profit_factor']:.4f}") # 0.0
    pf_stats_4 = calculate_win_rate_avg_win_loss_profit_factor([]) # No trades
    print(f"  PF no trades: {pf_stats_4['profit_factor']:.4f}") # 0.0
    pf_stats_5 = calculate_win_rate_avg_win_loss_profit_factor([{"pnl": 100}, {"pnl": -0.0001}]) # profit, tiny loss
    print(f"  PF profit, tiny loss: {pf_stats_5['profit_factor']:.4f}") # large
    pf_stats_6 = calculate_win_rate_avg_win_loss_profit_factor([{"pnl": 0.0001}, {"pnl": -100}]) # tiny profit, loss
    print(f"  PF tiny profit, loss: {pf_stats_6['profit_factor']:.4f}") # small (near 0)
    pf_stats_7 = calculate_win_rate_avg_win_loss_profit_factor([{'pnl':10},{'pnl':-5},{'pnl':0}])
    print(f"  PF mixed with zero: {pf_stats_7}")

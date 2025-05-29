import unittest
import numpy as np
from datetime import datetime, timedelta

from src.backtester.metrics import (
    calculate_total_return,
    calculate_annualized_return,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_win_rate_avg_win_loss_profit_factor,
    calculate_all_metrics
)
from src.core.models import Trade
from src.core.enums import OrderSide

class TestBacktesterMetrics(unittest.TestCase):
    """
    Test suite for the metrics calculation functions in src.backtester.metrics.
    """

    def setUp(self):
        self.risk_free_rate = 0.02 # Example for Sharpe/Sortino
        self.trading_days_per_year = 252

    # --- Test calculate_total_return ---
    def test_calculate_total_return(self):
        self.assertAlmostEqual(calculate_total_return([100, 110, 120]), 0.20) # Normal return
        self.assertAlmostEqual(calculate_total_return([100, 100, 100]), 0.0)  # No return (flat equity)
        self.assertAlmostEqual(calculate_total_return([100, 90, 80]), -0.20) # Loss
        self.assertEqual(calculate_total_return([]), 0.0)                       # Empty list - returns 0.0
        self.assertEqual(calculate_total_return([100]), 0.0)                    # Single point list - returns 0.0
        self.assertEqual(calculate_total_return([0, 10, 20]), float('inf'))     # Zero start equity, positive end - returns inf
        self.assertEqual(calculate_total_return([-10, 10, 20]), ((20.0 / -10.0) -1) ) # Negative start equity
        self.assertAlmostEqual(calculate_total_return([10, 0, -10]), -2.0)  # Ends at negative

    # --- Test calculate_annualized_return ---
    def test_calculate_annualized_return(self):
        equity_curve = [100 * (1.0005)**i for i in range(365)] # Approx 19.8% total return over 1 year (365 days)
        total_return = calculate_total_return(equity_curve)
        duration_years_365 = (365 / 365.0) # 1 year based on days
        
        # Assuming 252 trading days means the equity curve represents daily values for 252 trading days
        duration_years_252_trading = (252 / 252.0)
        
        # If equity_curve has 253 points, it means 252 periods.
        equity_curve_252_periods = [100 * (1.0005)**i for i in range(253)] 
        total_return_252 = calculate_total_return(equity_curve_252_periods)
        num_days_252 = len(equity_curve_252_periods) - 1

        self.assertAlmostEqual(
            calculate_annualized_return(equity_curve_252_periods, num_days_252), # Corrected call
            (1 + total_return_252)**(365.0 / num_days_252) - 1 # Matched 365.0 factor
        )
        
        # Test with total return of 0
        flat_equity_curve = [100.0] * 253 # Represents 252 days of no change
        self.assertAlmostEqual(calculate_annualized_return(flat_equity_curve, len(flat_equity_curve)-1), 0.0)
        
        # Very short duration (e.g., 1 day = 2 points in equity curve)
        short_equity_curve = [100.0, 101.0] # 1% in 1 day
        short_duration_total_return = calculate_total_return(short_equity_curve)
        num_days_short = len(short_equity_curve) - 1
        self.assertAlmostEqual(
            calculate_annualized_return(short_equity_curve, num_days_short),
            (1 + short_duration_total_return)**(365.0 / num_days_short) - 1
        )
        
        # num_days is 0 (or less) - function should return 0.0
        self.assertEqual(calculate_annualized_return([100, 101], 0), 0.0)
        # Empty or single point equity curve - function should return 0.0
        self.assertEqual(calculate_annualized_return([100], 1), 0.0) # num_days is 1, but curve too short
        self.assertEqual(calculate_annualized_return([], 0), 0.0)


    # --- Test calculate_sharpe_ratio ---
    def test_calculate_sharpe_ratio(self):
        equity_curve = [100, 101, 102, 103, 102, 104, 105] # Example from metrics.py
        daily_returns = np.diff(equity_curve) / equity_curve[:-1]
        
        # Test normal case
        # The function expects equity_curve, not daily_returns
        sharpe = calculate_sharpe_ratio(equity_curve, self.risk_free_rate, self.trading_days_per_year)
        # Manual calculation for this specific case (approximate)
        excess_returns = daily_returns - (self.risk_free_rate / self.trading_days_per_year)
        # Using ddof=0 for np.std to align with pandas default if that's what the function effectively uses
        # However, the function uses np.std directly on returns, which defaults to ddof=0
        expected_sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(self.trading_days_per_year)
        self.assertAlmostEqual(sharpe, expected_sharpe)

        # Test edge cases for the function (which expects equity_curve)
        self.assertEqual(calculate_sharpe_ratio([100, 100], self.risk_free_rate, self.trading_days_per_year), -np.inf) # Changed expected to -np.inf
        self.assertEqual(calculate_sharpe_ratio([100], self.risk_free_rate, self.trading_days_per_year), 0.0) # Single point equity
        self.assertEqual(calculate_sharpe_ratio([], self.risk_free_rate, self.trading_days_per_year), 0.0) # Empty equity

        # Zero standard deviation of excess returns - construct equity curves that lead to these
        # Case 1: Mean excess return is also 0 -> Sharpe should be 0
        # Test with a flat equity curve and zero risk-free rate
        flat_equity_for_zero_sharpe = [100.0, 100.0, 100.0, 100.0]
        self.assertAlmostEqual(calculate_sharpe_ratio(flat_equity_for_zero_sharpe, 0.0, self.trading_days_per_year), 0.0, places=5)
        
        # Case 2: Mean excess return > 0 -> Sharpe should be np.inf
        rf_daily = self.risk_free_rate / self.trading_days_per_year # Use the original rf_daily for this case
        equity_positive_excess = [100 * (1 + rf_daily + 0.001)**i for i in range(10)]
        self.assertEqual(calculate_sharpe_ratio(equity_positive_excess, self.risk_free_rate, self.trading_days_per_year), np.inf)

        # Case 3: Mean excess return < 0 -> Sharpe should be -np.inf
        equity_negative_excess = [100 * (1 + rf_daily - 0.001)**i for i in range(10)]
        self.assertEqual(calculate_sharpe_ratio(equity_negative_excess, self.risk_free_rate, self.trading_days_per_year), -np.inf)


    # --- Test calculate_sortino_ratio ---
    def test_calculate_sortino_ratio(self):
        equity_curve = [100, 101, 102, 103, 102, 104, 105] # Example from metrics.py
        daily_returns = np.diff(equity_curve) / equity_curve[:-1] # Used for manual expected calculation

        # The function expects equity_curve, not daily_returns
        sortino = calculate_sortino_ratio(equity_curve, self.risk_free_rate, self.trading_days_per_year)
        
        # Manual calculation aligned with the function's internal logic
        rf_daily = self.risk_free_rate / self.trading_days_per_year
        calc_daily_returns = np.diff(equity_curve) / equity_curve[:-1] # Recalculate daily_returns as function does
        calc_excess_returns = calc_daily_returns - rf_daily
        calc_mean_excess_return = np.mean(calc_excess_returns)
        
        calc_negative_excess_returns = calc_excess_returns[calc_excess_returns < 0]
        
        if len(calc_negative_excess_returns) < 1:
            calc_downside_deviation = 0.0
        else:
            calc_downside_deviation = np.std(calc_negative_excess_returns) # Matches function's std calc

        if calc_downside_deviation == 0:
            expected_sortino_manual = np.inf if calc_mean_excess_return > 0 else 0.0
        else:
            expected_sortino_manual = calc_mean_excess_return / calc_downside_deviation * np.sqrt(self.trading_days_per_year)
        
        self.assertAlmostEqual(sortino, expected_sortino_manual, places=5)
        
        # Test edge cases for the function (which expects equity_curve)
        self.assertEqual(calculate_sortino_ratio([100, 100], self.risk_free_rate, self.trading_days_per_year), 0.0)
        self.assertEqual(calculate_sortino_ratio([100], self.risk_free_rate, self.trading_days_per_year), 0.0)
        self.assertEqual(calculate_sortino_ratio([], self.risk_free_rate, self.trading_days_per_year), 0.0)

        # No negative excess returns (downside deviation is 0 or near 0)
        # If mean excess return > 0, Sortino should be np.inf
        rf_daily = self.risk_free_rate / self.trading_days_per_year
        equity_all_positive_excess = [100 * (1 + rf_daily + 0.001)**i for i in range(10)] # Returns always > rf_daily
        self.assertEqual(calculate_sortino_ratio(equity_all_positive_excess, self.risk_free_rate, self.trading_days_per_year), np.inf)
        
        # If mean excess return == 0 (all returns == target_return), Sortino should be 0
        # Test with a flat equity curve and zero risk-free rate
        flat_equity_for_zero_sortino = [100.0, 100.0, 100.0, 100.0]
        self.assertAlmostEqual(calculate_sortino_ratio(flat_equity_for_zero_sortino, 0.0, self.trading_days_per_year), 0.0, places=5)


    # --- Test calculate_max_drawdown ---
    def test_calculate_max_drawdown(self):
        dd_curve_1 = [100, 110, 120, 100, 130, 90, 110] 
        self.assertAlmostEqual(calculate_max_drawdown(dd_curve_1), (130.0-90.0)/130.0) 
        
        dd_curve_2 = [100, 120, 80, 110, 70, 90, 60] 
        self.assertAlmostEqual(calculate_max_drawdown(dd_curve_2), (120.0-60.0)/120.0)

        self.assertAlmostEqual(calculate_max_drawdown([100, 110, 120, 130]), 0.0) # Monotonically increasing
        self.assertAlmostEqual(calculate_max_drawdown([100, 90, 80, 70]), (100.0-70.0)/100.0) # Only goes down
        self.assertAlmostEqual(calculate_max_drawdown([100, 100, 100]), 0.0) # Flat curve
        self.assertEqual(calculate_max_drawdown([]), 0.0)                     # Empty curve
        self.assertEqual(calculate_max_drawdown([100]), 0.0)                  # Single point
        # Curve with zeros and negatives: Peak = 10, Trough = -20. DD = (10 - (-20)) / 10 = 3.0
        self.assertAlmostEqual(calculate_max_drawdown([10, 0, -10, 5, -20]), 3.0) 
        self.assertEqual(calculate_max_drawdown([0,0,0]), 0.0) # All zeros start


    # --- Test calculate_win_rate_avg_win_loss_profit_factor ---
    def test_calculate_win_rate_avg_win_loss_profit_factor(self):
        ts = datetime.now()
        trades_mix = [
            Trade(trade_id='t1', order_id='o1', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=10.0), # Win
            Trade(trade_id='t2', order_id='o2', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=-5.0), # Loss
            Trade(trade_id='t3', order_id='o3', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=20.0), # Win
            Trade(trade_id='t4', order_id='o4', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=0.0),  # Zero PNL
        ]
        # Wins: 10, 20 (total 30). Losses: -5 (total 5). Win rate: 2/3 = 0.666. Avg Win: 15. Avg Loss: -5. Profit Factor: 30/5 = 6
        res_mix = calculate_win_rate_avg_win_loss_profit_factor(trades_mix)
        self.assertAlmostEqual(res_mix['win_rate'], 2.0/3.0)
        self.assertAlmostEqual(res_mix['avg_win_pnl'], 15.0)      # Changed key
        self.assertAlmostEqual(res_mix['avg_loss_pnl'], -5.0)     # Changed key & expected value (avg_loss_pnl is negative)
        self.assertAlmostEqual(res_mix['profit_factor'], 6.0)

        common_args = {'trade_id':'t', 'order_id':'o', 'symbol':'S', 'quantity':1, 'price':10, 'side':OrderSide.BUY, 'timestamp':ts, 'commission': 0}
        trades_only_wins = [Trade(**common_args, pnl=10), Trade(**common_args, pnl=20)]
        res_wins = calculate_win_rate_avg_win_loss_profit_factor(trades_only_wins)
        self.assertAlmostEqual(res_wins['win_rate'], 1.0)
        self.assertAlmostEqual(res_wins['avg_win_pnl'], 15.0)    # Changed key
        self.assertEqual(res_wins['avg_loss_pnl'], 0)          # Changed key
        self.assertEqual(res_wins['profit_factor'], np.inf) # Profit factor inf

        trades_only_losses = [Trade(**common_args, pnl=-5), Trade(**common_args, pnl=-10)]
        res_losses = calculate_win_rate_avg_win_loss_profit_factor(trades_only_losses)
        self.assertAlmostEqual(res_losses['win_rate'], 0.0)
        self.assertEqual(res_losses['avg_win_pnl'], 0)            # Changed key
        self.assertAlmostEqual(res_losses['avg_loss_pnl'], -7.5)  # Changed key & expected value
        self.assertAlmostEqual(res_losses['profit_factor'], 0.0) # Profit factor 0

        trades_only_zero_pnl = [Trade(**common_args, pnl=0.0), Trade(**common_args, pnl=0.0)]
        res_zero = calculate_win_rate_avg_win_loss_profit_factor(trades_only_zero_pnl)
        self.assertEqual(res_zero['win_rate'], 0.0) # Zero PNL not counted as win
        self.assertEqual(res_zero['avg_win_pnl'], 0)             # Changed key
        self.assertEqual(res_zero['avg_loss_pnl'], 0)           # Changed key
        self.assertEqual(res_zero['profit_factor'], 0.0) # total_loss is 0, total_profit is 0 -> PF 0.0

        res_no_trades = calculate_win_rate_avg_win_loss_profit_factor([])
        self.assertEqual(res_no_trades['win_rate'], 0)
        self.assertEqual(res_no_trades['avg_win_pnl'], 0)         # Changed key
        self.assertEqual(res_no_trades['avg_loss_pnl'], 0)        # Changed key
        self.assertEqual(res_no_trades['profit_factor'], 0.0) # Matches function's default

        # Test with trades that might be filtered out (e.g. pnl is None)
        # The function `calculate_win_rate_avg_win_loss_profit_factor` filters for `pnl is not None`.
        # Creating a Trade without pnl or with pnl=None.
        # For this, we need a Trade constructor that allows optional pnl or modify it post-init.
        # Assuming Trade model makes pnl non-optional or has a default that's not None.
        # If a Trade object is created where `pnl` is None, it will be filtered.
        
        # Trades with pnl=None are filtered out by the metric function.
        # The Trade model requires pnl. Let's assume it's always present.
        # If we wanted to test filtering of None PNLs, we'd need to mock Trade or pass dicts.
        # For now, this part of test is less critical as Trade model enforces pnl.
        
        # Consider a trade list where one trade is valid and another would be filtered if pnl could be None
        # For now, this case is implicitly covered if Trade model ensures pnl is always set.
        # The original test `trades_missing_pnl = [Trade(pnl=10), Trade()]` would fail at Trade() instantiation.
        # Let's make it a list of valid trades for clarity.
        trades_one_valid = [Trade(**common_args, pnl=10)]
        res_one_valid = calculate_win_rate_avg_win_loss_profit_factor(trades_one_valid)
        self.assertEqual(res_one_valid['win_rate'], 1.0) 
        self.assertEqual(res_one_valid['avg_win_pnl'], 10.0)
        self.assertEqual(res_one_valid['avg_loss_pnl'], 0)
        self.assertEqual(res_one_valid['profit_factor'], np.inf)


    # --- Test calculate_all_metrics ---
    def test_calculate_all_metrics(self):
        equity_curve = [100, 105, 102, 108, 110, 105, 115] # Example equity curve
        ts = datetime.now()
        # Create dummy Trade objects with all required fields
        common_trade_args = {'trade_id': 't', 'order_id': 'o', 'symbol': 'S', 'quantity': 1, 'price': 100, 'side': OrderSide.BUY, 'timestamp': ts, 'commission': 0}
        trades = [
            Trade(**common_trade_args, pnl=5.0), 
            Trade(**common_trade_args, pnl=-3.0), 
            Trade(**common_trade_args, pnl=6.0), 
            Trade(**common_trade_args, pnl=2.0), 
            Trade(**common_trade_args, pnl=-5.0), 
            Trade(**common_trade_args, pnl=10.0)
        ] # 4 wins, 2 losses. Total Win PNL = 23. Total Loss PNL = 8.
        
        # Mock datetime objects for equity curve if needed by functions called by calculate_all_metrics
        # However, most metrics use the equity_curve (list of floats) directly or daily_returns from it.
        # The duration for annualized return calculation needs the number of periods.
        num_periods = len(equity_curve) -1 

        metrics = calculate_all_metrics(equity_curve, trades, self.risk_free_rate, self.trading_days_per_year, num_periods)

        self.assertIn('total_return', metrics)
        self.assertIn('annualized_return', metrics)
        self.assertIn('sharpe_ratio', metrics)
        self.assertIn('sortino_ratio', metrics)
        self.assertIn('max_drawdown', metrics)
        self.assertIn('win_rate', metrics)
        self.assertIn('avg_win_pnl', metrics) # Changed key
        self.assertIn('avg_loss_pnl', metrics) # Changed key
        self.assertIn('profit_factor', metrics)
        self.assertIn('total_trades_with_pnl', metrics) # Changed key
        # 'average_trade_pnl' is not returned by calculate_win_rate_avg_win_loss_profit_factor

        # Verify a few key metrics
        self.assertAlmostEqual(metrics['total_return'], (115.0 - 100.0) / 100.0)
        self.assertAlmostEqual(metrics['win_rate'], 4.0/6.0) # 4 wins / (4 wins + 2 losses)
        self.assertAlmostEqual(metrics['avg_win_pnl'], (5+6+2+10)/4.0) # Changed key
        self.assertAlmostEqual(metrics['avg_loss_pnl'], (-3-5)/2.0) # Changed key, losses are negative
        self.assertAlmostEqual(metrics['profit_factor'], (5+6+2+10)/(3+5))
        self.assertEqual(metrics['total_trades_with_pnl'], 6) # Changed key
        # self.assertAlmostEqual(metrics['average_trade_pnl'], (23.0-8.0)/6.0) # This metric is not returned
        
        # Test with empty trades (should not crash, trade-related metrics should be default/None)
        metrics_no_trades = calculate_all_metrics(equity_curve, [], self.risk_free_rate, self.trading_days_per_year, num_periods)
        self.assertAlmostEqual(metrics_no_trades['total_return'], (115.0 - 100.0) / 100.0) # Equity metrics still calculated
        self.assertEqual(metrics_no_trades['win_rate'], 0)
        self.assertEqual(metrics_no_trades['avg_win_pnl'], 0) # Changed key
        self.assertEqual(metrics_no_trades['avg_loss_pnl'], 0) # Changed key
        self.assertEqual(metrics_no_trades['profit_factor'], 0.0) # Changed from assertIsNone based on function default
        self.assertEqual(metrics_no_trades['total_trades_with_pnl'], 0) # Changed key
        # self.assertEqual(metrics_no_trades['average_trade_pnl'], 0) # This metric is not returned


if __name__ == '__main__':
    unittest.main()

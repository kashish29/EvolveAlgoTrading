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
        self.assertIsNone(calculate_total_return([]))                       # Empty list
        self.assertIsNone(calculate_total_return([100]))                    # Single point list
        self.assertIsNone(calculate_total_return([0, 10, 20]))              # Zero start equity
        self.assertIsNone(calculate_total_return([-10, 10, 20]))            # Negative start equity
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

        self.assertAlmostEqual(
            calculate_annualized_return(total_return_252, len(equity_curve_252_periods)-1, self.trading_days_per_year),
            (1 + total_return_252)**(self.trading_days_per_year / (len(equity_curve_252_periods)-1)) - 1
        )
        self.assertAlmostEqual(calculate_annualized_return(0.0, 252, self.trading_days_per_year), 0.0) # Total return of 0
        
        # Very short duration (e.g., 1 day = 2 points in equity curve)
        short_duration_total_return = 0.01 # 1% in 1 day
        self.assertAlmostEqual(
            calculate_annualized_return(short_duration_total_return, 1, self.trading_days_per_year),
            (1 + short_duration_total_return)**(self.trading_days_per_year / 1) - 1
        )
        self.assertIsNone(calculate_annualized_return(0.1, 0, self.trading_days_per_year)) # num_periods is 0
        self.assertIsNone(calculate_annualized_return(None, 252, self.trading_days_per_year))


    # --- Test calculate_sharpe_ratio ---
    def test_calculate_sharpe_ratio(self):
        equity_curve = [100, 101, 102, 103, 102, 104, 105] # Example from metrics.py
        daily_returns = np.diff(equity_curve) / equity_curve[:-1]
        
        # Test normal case
        sharpe = calculate_sharpe_ratio(daily_returns, self.risk_free_rate, self.trading_days_per_year)
        # Manual calculation for this specific case (approximate)
        excess_returns = daily_returns - (self.risk_free_rate / self.trading_days_per_year)
        expected_sharpe = np.mean(excess_returns) / np.std(excess_returns, ddof=1) * np.sqrt(self.trading_days_per_year)
        self.assertAlmostEqual(sharpe, expected_sharpe)

        self.assertIsNone(calculate_sharpe_ratio(np.array([]), self.risk_free_rate, self.trading_days_per_year)) # Empty returns
        self.assertIsNone(calculate_sharpe_ratio(np.array([0.01]), self.risk_free_rate, self.trading_days_per_year)) # Too short (needs >1 for std dev)

        # Zero standard deviation of excess returns
        # Case 1: Mean excess return is also 0 -> Sharpe should be 0
        zero_std_returns_mean_zero = np.array([self.risk_free_rate / self.trading_days_per_year] * 10)
        self.assertAlmostEqual(calculate_sharpe_ratio(zero_std_returns_mean_zero, self.risk_free_rate, self.trading_days_per_year), 0.0)
        
        # Case 2: Mean excess return > 0 -> Sharpe should be np.inf
        positive_mean_excess_returns = np.array([(self.risk_free_rate / self.trading_days_per_year) + 0.001] * 10)
        self.assertEqual(calculate_sharpe_ratio(positive_mean_excess_returns, self.risk_free_rate, self.trading_days_per_year), np.inf)

        # Case 3: Mean excess return < 0 -> Sharpe should be -np.inf
        negative_mean_excess_returns = np.array([(self.risk_free_rate / self.trading_days_per_year) - 0.001] * 10)
        self.assertEqual(calculate_sharpe_ratio(negative_mean_excess_returns, self.risk_free_rate, self.trading_days_per_year), -np.inf)


    # --- Test calculate_sortino_ratio ---
    def test_calculate_sortino_ratio(self):
        equity_curve = [100, 101, 102, 103, 102, 104, 105] # Example from metrics.py
        daily_returns = np.diff(equity_curve) / equity_curve[:-1]

        sortino = calculate_sortino_ratio(daily_returns, self.risk_free_rate, self.trading_days_per_year)
        # Manual calculation (approximate)
        mean_daily_return = np.mean(daily_returns)
        target_return = self.risk_free_rate / self.trading_days_per_year
        negative_excess_returns = daily_returns[daily_returns < target_return] - target_return
        downside_deviation = np.sqrt(np.sum(negative_excess_returns**2) / len(daily_returns))
        expected_sortino = (mean_daily_return - target_return) / downside_deviation * np.sqrt(self.trading_days_per_year)
        self.assertAlmostEqual(sortino, expected_sortino)
        
        self.assertIsNone(calculate_sortino_ratio(np.array([]), self.risk_free_rate, self.trading_days_per_year)) # Empty
        self.assertIsNone(calculate_sortino_ratio(np.array([0.01]), self.risk_free_rate, self.trading_days_per_year)) # Too short

        # No negative excess returns (downside deviation is 0)
        # If mean excess return > 0, Sortino should be np.inf
        all_positive_excess_returns = np.array([0.01, 0.02, 0.005]) + (self.risk_free_rate / self.trading_days_per_year)
        self.assertEqual(calculate_sortino_ratio(all_positive_excess_returns, self.risk_free_rate, self.trading_days_per_year), np.inf)
        
        # If mean excess return == 0 (all returns == target_return), Sortino should be 0
        all_target_returns = np.array([self.risk_free_rate / self.trading_days_per_year] * 10)
        self.assertAlmostEqual(calculate_sortino_ratio(all_target_returns, self.risk_free_rate, self.trading_days_per_year), 0.0)

        # If mean excess return < 0, and downside deviation is 0 (should not happen if returns are consistently below target but not equal)
        # This case is tricky, if all returns are equal and below target, downside dev is non-zero.
        # If downside deviation is truly zero, and mean excess return is negative, it implies all returns are target_return, leading to 0.

        # Zero downside deviation (all returns >= target_return)
        returns_at_or_above_target = np.array([0.01, 0.02, 0.005]) + (self.risk_free_rate / self.trading_days_per_year)
        self.assertEqual(calculate_sortino_ratio(returns_at_or_above_target, self.risk_free_rate, self.trading_days_per_year), np.inf)
        
        returns_equal_target = np.full(5, self.risk_free_rate / self.trading_days_per_year)
        self.assertAlmostEqual(calculate_sortino_ratio(returns_equal_target, self.risk_free_rate, self.trading_days_per_year), 0.0)


    # --- Test calculate_max_drawdown ---
    def test_calculate_max_drawdown(self):
        dd_curve_1 = [100, 110, 120, 100, 130, 90, 110] # From metrics.py example: Peak 130, Trough 90 -> (90-130)/130 = -0.3076
        self.assertAlmostEqual(calculate_max_drawdown(dd_curve_1), (90.0-130.0)/130.0) 
        
        dd_curve_2 = [100, 120, 80, 110, 70, 90, 60] # Peak 120, Trough 60 -> (60-120)/120 = -0.5
        self.assertAlmostEqual(calculate_max_drawdown(dd_curve_2), (60.0-120.0)/120.0)

        self.assertAlmostEqual(calculate_max_drawdown([100, 110, 120, 130]), 0.0) # Monotonically increasing
        self.assertAlmostEqual(calculate_max_drawdown([100, 90, 80, 70]), (70.0-100.0)/100.0) # Only goes down
        self.assertAlmostEqual(calculate_max_drawdown([100, 100, 100]), 0.0) # Flat curve
        self.assertIsNone(calculate_max_drawdown([]))                     # Empty curve
        self.assertIsNone(calculate_max_drawdown([100]))                  # Single point
        self.assertAlmostEqual(calculate_max_drawdown([10, 0, -10, 5, -20]), (-20.0-10.0)/10.0) # Curve with zeros and negatives
        self.assertIsNone(calculate_max_drawdown([0,0,0])) # All zeros start


    # --- Test calculate_win_rate_avg_win_loss_profit_factor ---
    def test_calculate_win_rate_avg_win_loss_profit_factor(self):
        ts = datetime.now()
        trades_mix = [
            Trade(trade_id='t1', order_id='o1', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=10.0), # Win
            Trade(trade_id='t2', order_id='o2', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=-5.0), # Loss
            Trade(trade_id='t3', order_id='o3', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=20.0), # Win
            Trade(trade_id='t4', order_id='o4', symbol='S', quantity=1, price=10, side=OrderSide.BUY, timestamp=ts, pnl=0.0),  # Zero PNL
        ]
        # Wins: 10, 20 (total 30). Losses: -5 (total 5). Win rate: 2/3 = 0.666. Avg Win: 15. Avg Loss: 5. Profit Factor: 30/5 = 6
        res_mix = calculate_win_rate_avg_win_loss_profit_factor(trades_mix)
        self.assertAlmostEqual(res_mix['win_rate'], 2.0/3.0)
        self.assertAlmostEqual(res_mix['average_win'], 15.0)
        self.assertAlmostEqual(res_mix['average_loss'], 5.0)
        self.assertAlmostEqual(res_mix['profit_factor'], 6.0)

        trades_only_wins = [Trade(pnl=10), Trade(pnl=20)]
        res_wins = calculate_win_rate_avg_win_loss_profit_factor(trades_only_wins)
        self.assertAlmostEqual(res_wins['win_rate'], 1.0)
        self.assertAlmostEqual(res_wins['average_win'], 15.0)
        self.assertEqual(res_wins['average_loss'], 0) # No losses
        self.assertEqual(res_wins['profit_factor'], np.inf) # Profit factor inf

        trades_only_losses = [Trade(pnl=-5), Trade(pnl=-10)]
        res_losses = calculate_win_rate_avg_win_loss_profit_factor(trades_only_losses)
        self.assertAlmostEqual(res_losses['win_rate'], 0.0)
        self.assertEqual(res_losses['average_win'], 0) # No wins
        self.assertAlmostEqual(res_losses['average_loss'], 7.5)
        self.assertAlmostEqual(res_losses['profit_factor'], 0.0) # Profit factor 0

        trades_only_zero_pnl = [Trade(pnl=0.0), Trade(pnl=0.0)]
        res_zero = calculate_win_rate_avg_win_loss_profit_factor(trades_only_zero_pnl)
        self.assertEqual(res_zero['win_rate'], 0.0) # Zero PNL not counted as win
        self.assertEqual(res_zero['average_win'], 0)
        self.assertEqual(res_zero['average_loss'], 0)
        self.assertIsNone(res_zero['profit_factor']) # Neither wins nor losses, total_loss is 0

        res_no_trades = calculate_win_rate_avg_win_loss_profit_factor([])
        self.assertEqual(res_no_trades['win_rate'], 0)
        self.assertEqual(res_no_trades['average_win'], 0)
        self.assertEqual(res_no_trades['average_loss'], 0)
        self.assertIsNone(res_no_trades['profit_factor'])

        trades_missing_pnl = [Trade(pnl=10), Trade()] # One trade missing pnl (will be ignored)
        res_missing = calculate_win_rate_avg_win_loss_profit_factor(trades_missing_pnl)
        self.assertEqual(res_missing['win_rate'], 1.0) # Based on the one valid trade
        self.assertEqual(res_missing['average_win'], 10.0)
        self.assertEqual(res_missing['average_loss'], 0)
        self.assertEqual(res_missing['profit_factor'], np.inf)
        
        trades_all_pnl_none = [Trade(pnl=None), Trade(pnl=None)]
        res_all_none = calculate_win_rate_avg_win_loss_profit_factor(trades_all_pnl_none)
        self.assertEqual(res_all_none['win_rate'], 0)
        self.assertEqual(res_all_none['average_win'], 0)
        self.assertEqual(res_all_none['average_loss'], 0)
        self.assertIsNone(res_all_none['profit_factor'])


    # --- Test calculate_all_metrics ---
    def test_calculate_all_metrics(self):
        equity_curve = [100, 105, 102, 108, 110, 105, 115] # Example equity curve
        ts = datetime.now()
        trades = [
            Trade(pnl=5.0), Trade(pnl=-3.0), Trade(pnl=6.0), Trade(pnl=2.0), Trade(pnl=-5.0), Trade(pnl=10.0)
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
        self.assertIn('average_win', metrics)
        self.assertIn('average_loss', metrics)
        self.assertIn('profit_factor', metrics)
        self.assertIn('total_trades', metrics)
        self.assertIn('average_trade_pnl', metrics)

        # Verify a few key metrics
        self.assertAlmostEqual(metrics['total_return'], (115.0 - 100.0) / 100.0)
        self.assertAlmostEqual(metrics['win_rate'], 4.0/6.0)
        self.assertAlmostEqual(metrics['average_win'], (5+6+2+10)/4.0)
        self.assertAlmostEqual(metrics['average_loss'], (3+5)/2.0)
        self.assertAlmostEqual(metrics['profit_factor'], (5+6+2+10)/(3+5))
        self.assertEqual(metrics['total_trades'], 6)
        self.assertAlmostEqual(metrics['average_trade_pnl'], (23.0-8.0)/6.0)
        
        # Test with empty trades (should not crash, trade-related metrics should be default/None)
        metrics_no_trades = calculate_all_metrics(equity_curve, [], self.risk_free_rate, self.trading_days_per_year, num_periods)
        self.assertAlmostEqual(metrics_no_trades['total_return'], (115.0 - 100.0) / 100.0) # Equity metrics still calculated
        self.assertEqual(metrics_no_trades['win_rate'], 0)
        self.assertEqual(metrics_no_trades['average_win'], 0)
        self.assertEqual(metrics_no_trades['average_loss'], 0)
        self.assertIsNone(metrics_no_trades['profit_factor'])
        self.assertEqual(metrics_no_trades['total_trades'], 0)
        self.assertEqual(metrics_no_trades['average_trade_pnl'], 0)


if __name__ == '__main__':
    unittest.main()

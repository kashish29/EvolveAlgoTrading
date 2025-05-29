import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import quantstats.stats as qs_stats # Crucial import

from src.analytics.performance_reporter import PerformanceReporter
from src.backtester.metrics import calculate_win_rate_avg_win_loss_profit_factor # For comparison
from src.core.models import Trade
from src.core.enums import OrderSide

class TestPerformanceReporterCalculateKeyMetrics(unittest.TestCase):
    """
    Test suite for the calculate_key_metrics() method of PerformanceReporter.
    """

    def setUp(self):
        # Sample data for equity curve
        self.equity_dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'])
        self.equity_values = [100.0, 102.0, 101.0, 103.0, 105.0] # Example values
        self.sample_equity_curve_series = pd.Series(self.equity_values, index=self.equity_dates)

        # Sample data for trades
        self.sample_trades_data = [
            {'trade_id': 't1', 'order_id': 'o1', 'symbol': 'SYM1', 'quantity': 10, 'price': 10.0, 'side': OrderSide.BUY, 'timestamp': datetime(2023,1,1), 'commission': 1.0, 'pnl': 20.0}, # Win
            {'trade_id': 't2', 'order_id': 'o2', 'symbol': 'SYM1', 'quantity': 10, 'price': 12.0, 'side': OrderSide.SELL, 'timestamp': datetime(2023,1,2), 'commission': 1.0, 'pnl': -10.0}, # Loss
            {'trade_id': 't3', 'order_id': 'o3', 'symbol': 'SYM1', 'quantity': 5, 'price': 9.0, 'side': OrderSide.BUY, 'timestamp': datetime(2023,1,3), 'commission': 0.5, 'pnl': 15.0},  # Win
            {'trade_id': 't4', 'order_id': 'o4', 'symbol': 'SYM1', 'quantity': 5, 'price': 12.0, 'side': OrderSide.SELL, 'timestamp': datetime(2023,1,4), 'commission': 0.5, 'pnl': 0.0},   # Zero PNL
        ]
        self.sample_trades_df = pd.DataFrame(self.sample_trades_data)
        
        # Convert to Trade objects for backtester.metrics comparison
        self.list_of_trade_objects = [Trade(**data) for data in self.sample_trades_data]
        
        self.default_risk_free_rate = 0.0 # Assuming this for reporter if not in config
        self.trading_days_per_year = 252 # Default in PerformanceReporter


    # --- Test Case 1: Equity-Based Metrics vs. Direct QuantStats Calls ---
    def test_equity_based_metrics_vs_quantstats(self):
        # 4.b. Instantiate PerformanceReporter
        # Reporter will use default config, so risk_free_rate should be 0.0
        reporter = PerformanceReporter(
            trades_df=pd.DataFrame(columns=['pnl']), # Empty trades for this part
            equity_curve_series=self.sample_equity_curve_series.copy()
        )
        
        # 4.c. Call calculate_key_metrics
        metrics = reporter.calculate_key_metrics()

        # 4.d. If reporter.daily_returns is not empty
        self.assertFalse(reporter.daily_returns.empty, "Daily returns should not be empty for this test.")
        
        current_risk_free_rate = reporter.config.get('risk_free_rate', self.default_risk_free_rate)

        # i. Sharpe Ratio
        expected_sharpe = qs_stats.sharpe(reporter.daily_returns, risk_free=current_risk_free_rate, periods=self.trading_days_per_year)
        self.assertAlmostEqual(metrics["Sharpe Ratio"], expected_sharpe, places=5)
        
        # ii. Sortino Ratio
        expected_sortino = qs_stats.sortino(reporter.daily_returns, risk_free=current_risk_free_rate, periods=self.trading_days_per_year)
        # Handle np.nan for Sortino if expected is also nan (e.g. no downside deviation)
        if np.isnan(expected_sortino):
            self.assertTrue(np.isnan(metrics["Sortino Ratio"]))
        else:
            self.assertAlmostEqual(metrics["Sortino Ratio"], expected_sortino, places=5)
            
        # iii. Max Drawdown
        self.assertAlmostEqual(metrics["Max Drawdown [%]"] / 100.0, qs_stats.max_drawdown(reporter.daily_returns), places=5)
        # iv. Total Return (Compounded)
        self.assertAlmostEqual(metrics["Total Return [%]"] / 100.0, qs_stats.comp(reporter.daily_returns), places=5)
        # v. CAGR and Calmar 
        self.assertAlmostEqual(metrics["CAGR [%]"] / 100.0, qs_stats.cagr(reporter.daily_returns, rf=current_risk_free_rate), places=5)
        self.assertAlmostEqual(metrics["Calmar Ratio"], qs_stats.calmar(reporter.daily_returns), places=5)


    def test_equity_based_metrics_empty_equity_curve(self):
        # 4.e. Test with an empty equity_curve
        empty_equity_curve = pd.Series(dtype=float)
        reporter_empty_equity = PerformanceReporter(
            trades_df=pd.DataFrame(columns=['pnl']),
            equity_curve_series=empty_equity_curve
        )
        metrics_empty_equity = reporter_empty_equity.calculate_key_metrics()

        self.assertTrue(reporter_empty_equity.daily_returns.empty, "Daily returns should be empty.")
        
        self.assertEqual(metrics_empty_equity["Total Return [%]"], 0.0)
        self.assertEqual(metrics_empty_equity["CAGR [%]"], 0.0)
        self.assertEqual(metrics_empty_equity["Max Drawdown [%]"], 0.0)
        # qs_stats with empty input or all NaNs might return 0 or np.nan. Reporter normalizes these to 0.0.
        self.assertEqual(metrics_empty_equity["Sharpe Ratio"], 0.0) 
        self.assertEqual(metrics_empty_equity["Sortino Ratio"], 0.0)
        self.assertEqual(metrics_empty_equity["Calmar Ratio"], 0.0)

    # --- Test Case 2: Trade-Based Metrics vs. src.backtester.metrics.py ---
    def test_trade_based_metrics_vs_backtester_metrics(self):
        # 5.b. Instantiate PerformanceReporter
        minimal_equity = pd.Series([100, 101], index=pd.to_datetime(['2023-01-01', '2023-01-02']))
        reporter = PerformanceReporter(
            trades_df=self.sample_trades_df.copy(),
            equity_curve_series=minimal_equity 
        )
        
        # 5.c. Call calculate_key_metrics
        reporter_metrics = reporter.calculate_key_metrics()
        
        # 5.e. Call calculate_win_rate_avg_win_loss_profit_factor
        backtester_trade_stats = calculate_win_rate_avg_win_loss_profit_factor(self.list_of_trade_objects)

        # f. Win Rate
        self.assertAlmostEqual(reporter_metrics["Win Rate [%]"] / 100.0, backtester_trade_stats["win_rate"], places=5)
        # g. Profit Factor
        if backtester_trade_stats["profit_factor"] == np.inf:
            self.assertEqual(reporter_metrics["Profit Factor"], np.inf)
        elif pd.isna(backtester_trade_stats["profit_factor"]): # Handle None/NaN from backtester_metrics
             self.assertTrue(pd.isna(reporter_metrics["Profit Factor"]))
        else:
            self.assertAlmostEqual(reporter_metrics["Profit Factor"], backtester_trade_stats["profit_factor"], places=5)
        # h. Avg Winning Trade PnL
        self.assertAlmostEqual(reporter_metrics["Avg Winning Trade PnL"], backtester_trade_stats["average_win"], places=5)
        # i. Avg Losing Trade PnL
        self.assertAlmostEqual(reporter_metrics["Avg Losing Trade PnL"], backtester_trade_stats["average_loss"], places=5)
        
        self.assertEqual(reporter_metrics["Total Trades"], len(self.list_of_trade_objects))
        
        total_pnl_reporter = self.sample_trades_df['pnl'].sum()
        avg_trade_pnl_reporter = total_pnl_reporter / len(self.list_of_trade_objects) if len(self.list_of_trade_objects) > 0 else 0
        self.assertAlmostEqual(reporter_metrics["Avg Trade PnL"], avg_trade_pnl_reporter, places=5)


    def test_trade_based_metrics_empty_trades_df(self):
        # 5.j. Test with an empty trades_df
        empty_trades_df = pd.DataFrame(columns=['pnl', 'symbol', 'timestamp', 'quantity', 'price', 'side', 'order_id', 'trade_id', 'commission'])
        minimal_equity = pd.Series([100, 101], index=pd.to_datetime(['2023-01-01', '2023-01-02']))
        reporter_empty_trades = PerformanceReporter(
            trades_df=empty_trades_df,
            equity_curve_series=minimal_equity
        )
        metrics_empty_trades = reporter_empty_trades.calculate_key_metrics()

        self.assertEqual(metrics_empty_trades["Total Trades"], 0)
        self.assertEqual(metrics_empty_trades["Win Rate [%]"], 0.0)
        self.assertEqual(metrics_empty_trades["Avg Winning Trade PnL"], 0.0)
        self.assertEqual(metrics_empty_trades["Avg Losing Trade PnL"], 0.0)
        # Profit factor for no trades should be 0.0 as per PerformanceReporter's handling
        self.assertEqual(metrics_empty_trades["Profit Factor"], 0.0)
        self.assertEqual(metrics_empty_trades["Avg Trade PnL"], 0.0)

if __name__ == '__main__':
    unittest.main()

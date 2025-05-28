import unittest
from unittest.mock import patch, MagicMock, call
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Assuming PerformanceReporter is in src.analytics.performance_reporter
# Adjust the import path if your project structure is different.
# For the testing environment, we might need to adjust Python's path or use relative imports if structured as a package.
# Let's assume the file is found via PYTHONPATH or similar mechanism for now.
from src.analytics.performance_reporter import PerformanceReporter

# Helper function to create sample equity curve (portfolio values)
def create_sample_equity_curve(start_date_str='2023-01-01', num_days=30, initial_equity=100000, daily_change_mean=100, daily_change_std=500):
    dates = pd.to_datetime([datetime.strptime(start_date_str, '%Y-%m-%d') + timedelta(days=i) for i in range(num_days)])
    equity_values = [initial_equity]
    np.random.seed(42) # for reproducibility
    for _ in range(1, num_days):
        change = np.random.normal(daily_change_mean, daily_change_std)
        equity_values.append(equity_values[-1] + change)
    return pd.Series(equity_values, index=dates, name="Equity")

# Helper function to create sample trades DataFrame
def create_sample_trades_df(num_trades=10, symbols=['AAPL', 'GOOG'], initial_pnl=50, pnl_increment=10):
    if num_trades == 0:
        return pd.DataFrame(columns=['entry_timestamp', 'exit_timestamp', 'symbol', 'pnl'])
    
    data = {
        'entry_timestamp': pd.to_datetime(['2023-01-01'] * num_trades) + pd.to_timedelta(np.arange(num_trades), unit='D'),
        'exit_timestamp': pd.to_datetime(['2023-01-02'] * num_trades) + pd.to_timedelta(np.arange(num_trades), unit='D'),
        'symbol': [symbols[i % len(symbols)] for i in range(num_trades)],
        'pnl': [initial_pnl + i * pnl_increment for i in range(num_trades)] # Example PnL data
    }
    return pd.DataFrame(data)

class TestPerformanceReporter(unittest.TestCase):

    def setUp(self):
        self.default_equity_curve = create_sample_equity_curve()
        self.default_trades = create_sample_trades_df()
        self.default_benchmark = create_sample_equity_curve(daily_change_mean=50, daily_change_std=200).pct_change().dropna().rename("Benchmark")
        self.reporter = PerformanceReporter(self.default_trades, self.default_equity_curve, self.default_benchmark)

    # 1. __init__ and _calculate_daily_returns
    def test_init_and_calculate_daily_returns_valid_equity_curve(self):
        self.assertIsInstance(self.reporter.daily_returns, pd.Series)
        self.assertFalse(self.reporter.daily_returns.empty)
        
        # Check calculation: equity_t / equity_{t-1} - 1
        # Resample to daily first
        daily_equity = self.default_equity_curve.resample('D').last()
        expected_returns = daily_equity.pct_change().dropna()
        expected_returns.index = expected_returns.index.normalize()

        pd.testing.assert_series_equal(self.reporter.daily_returns, expected_returns, check_dtype=False, atol=1e-6)

    def test_init_with_non_datetimeindex_equity_curve(self):
        equity_non_dt_index = self.default_equity_curve.copy()
        equity_non_dt_index.index = range(len(equity_non_dt_index))
        
        with patch('builtins.print') as mock_print: # Suppress print warnings during test
            reporter_non_dt = PerformanceReporter(self.default_trades, equity_non_dt_index)
            # It should attempt conversion. If successful, daily_returns will be calculated.
            # The PerformanceReporter's __init__ tries to convert.
            # The conversion to DatetimeIndex will happen, but for a range index,
            # it will result in NaT values, leading to empty daily_returns after dropna().
            # So, we expect daily_returns to be empty in this specific scenario.
            self.assertTrue(isinstance(reporter_non_dt.equity_curve.index, pd.DatetimeIndex))
            self.assertTrue(reporter_non_dt.daily_returns.empty, "Daily returns should be empty for non-meaningful datetime index.")


    def test_init_with_empty_equity_curve(self):
        empty_equity = pd.Series(dtype=float)
        with patch('builtins.print') as mock_print:
            reporter_empty = PerformanceReporter(self.default_trades, empty_equity)
        self.assertTrue(reporter_empty.daily_returns.empty)

    def test_init_with_short_equity_curve(self):
        short_equity = pd.Series([100000], index=[pd.to_datetime('2023-01-01')])
        with patch('builtins.print') as mock_print:
            reporter_short = PerformanceReporter(self.default_trades, short_equity)
        self.assertTrue(reporter_short.daily_returns.empty) # pct_change on 1 item is NaN, then dropped

    def test_init_with_and_without_benchmark(self):
        reporter_with_bm = PerformanceReporter(self.default_trades, self.default_equity_curve, benchmark_returns=self.default_benchmark)
        self.assertIsNotNone(reporter_with_bm.benchmark_returns)
        
        reporter_without_bm = PerformanceReporter(self.default_trades, self.default_equity_curve, benchmark_returns=None)
        self.assertIsNone(reporter_without_bm.benchmark_returns)

    # 2. generate_quantstats_report
    @patch('src.analytics.performance_reporter.quantstats.reports.html')
    def test_generate_quantstats_report(self, mock_qs_html):
        output_file = "test_report.html"
        report_title = "Test Report Title"
        
        # Normalize daily_returns index for comparison as quantstats does
        expected_returns = self.reporter.daily_returns.copy()
        expected_returns.index = expected_returns.index.normalize()

        expected_benchmark = self.reporter.benchmark_returns.copy()
        expected_benchmark.index = expected_benchmark.index.normalize()
        
        # Simulate alignment that make_portfolio might do
        # For this test, we assume make_portfolio is called correctly within the method.
        # We are primarily testing if quantstats.reports.html is called with appropriate series.
        
        self.reporter.generate_quantstats_report(output_path=output_file, title=report_title)
        
        args, kwargs = mock_qs_html.call_args
        # args[0] should be the returns series
        pd.testing.assert_series_equal(args[0], expected_returns, check_names=False, atol=1e-6)
        # kwargs['benchmark'] should be the benchmark series
        pd.testing.assert_series_equal(kwargs['benchmark'], expected_benchmark, check_names=False, atol=1e-6)
        self.assertEqual(kwargs['output'], output_file)
        self.assertEqual(kwargs['title'], report_title)

    @patch('src.analytics.performance_reporter.quantstats.reports.html')
    def test_generate_quantstats_report_no_benchmark(self, mock_qs_html):
        reporter_no_bm = PerformanceReporter(self.default_trades, self.default_equity_curve, benchmark_returns=None)
        reporter_no_bm.generate_quantstats_report() # Default path and title
        
        args, kwargs = mock_qs_html.call_args
        self.assertIsNone(kwargs['benchmark'])
        self.assertEqual(kwargs['output'], "report.html") # Default output
        self.assertEqual(kwargs['title'], "Strategy Performance") # Default title

    # 3. calculate_key_metrics
    def test_calculate_key_metrics_profitable_scenario(self):
        # Create data for a profitable strategy
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        equity = pd.Series([100, 110, 120, 115, 125], index=dates) # Ends higher
        trades = pd.DataFrame({
            'pnl': [10, 10, -5, 10], 
            'entry_timestamp': dates[:4], 'exit_timestamp': dates[1:], 'symbol': ['X']*4
        })
        reporter = PerformanceReporter(trades, equity)
        metrics = reporter.calculate_key_metrics()

        self.assertAlmostEqual(metrics["Total Return [%]"], 25.0, places=2) # (125/100 - 1)*100
        self.assertGreater(metrics["Sharpe Ratio"], 0) # Profitable, expect positive Sharpe
        self.assertEqual(metrics["Total Trades"], 4)
        self.assertAlmostEqual(metrics["Win Rate [%]"], 75.0, places=2) # 3 wins / 4 trades
        self.assertAlmostEqual(metrics["Profit Factor"], (10+10+10)/5, places=2) # 30 / 5
        self.assertAlmostEqual(metrics["Avg Winning Trade PnL"], (10+10+10)/3, places=2)
        self.assertAlmostEqual(metrics["Avg Losing Trade PnL"], -5.0, places=2)

    def test_calculate_key_metrics_losing_scenario(self):
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        equity = pd.Series([100, 90, 80, 85, 75], index=dates) # Ends lower
        trades = pd.DataFrame({
            'pnl': [-10, -10, 5, -10],
            'entry_timestamp': dates[:4], 'exit_timestamp': dates[1:], 'symbol': ['X']*4
        })
        reporter = PerformanceReporter(trades, equity)
        metrics = reporter.calculate_key_metrics()

        self.assertAlmostEqual(metrics["Total Return [%]"], -25.0, places=2) # (75/100 - 1)*100
        self.assertLess(metrics["Sharpe Ratio"], 0) # Losing, expect negative Sharpe
        self.assertEqual(metrics["Total Trades"], 4)
        self.assertAlmostEqual(metrics["Win Rate [%]"], 25.0, places=2) # 1 win / 4 trades
        self.assertAlmostEqual(metrics["Profit Factor"], 5/30, places=2) 
        self.assertAlmostEqual(metrics["Avg Winning Trade PnL"], 5.0, places=2)
        self.assertAlmostEqual(metrics["Avg Losing Trade PnL"], (-10-10-10)/3, places=2)

    def test_calculate_key_metrics_no_trades(self):
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        equity = pd.Series([100, 105, 102, 108, 110], index=dates) # Equity can still change
        no_trades = create_sample_trades_df(num_trades=0)
        reporter = PerformanceReporter(no_trades, equity)
        metrics = reporter.calculate_key_metrics()

        self.assertAlmostEqual(metrics["Total Return [%]"], 10.0, places=2)
        self.assertEqual(metrics["Total Trades"], 0)
        self.assertEqual(metrics["Win Rate [%]"], 0)
        self.assertEqual(metrics["Profit Factor"], 0) # Or some other indicator for no trades
        self.assertEqual(metrics["Avg Winning Trade PnL"], 0)
        self.assertEqual(metrics["Avg Losing Trade PnL"], 0)
    
    def test_calculate_key_metrics_all_winning_trades(self):
        dates = pd.date_range(start='2023-01-01', periods=3, freq='D')
        equity = pd.Series([100, 110, 120], index=dates)
        trades = pd.DataFrame({'pnl': [10, 10], 'entry_timestamp': dates[:2], 'exit_timestamp': dates[1:], 'symbol': ['X']*2})
        reporter = PerformanceReporter(trades, equity)
        metrics = reporter.calculate_key_metrics()
        self.assertEqual(metrics["Win Rate [%]"], 100.0)
        self.assertEqual(metrics["Profit Factor"], float('inf')) # No losses
        self.assertEqual(metrics["Avg Losing Trade PnL"], 0)

    def test_calculate_key_metrics_all_losing_trades(self):
        dates = pd.date_range(start='2023-01-01', periods=3, freq='D')
        equity = pd.Series([100, 90, 80], index=dates)
        trades = pd.DataFrame({'pnl': [-10, -10], 'entry_timestamp': dates[:2], 'exit_timestamp': dates[1:], 'symbol': ['X']*2})
        reporter = PerformanceReporter(trades, equity)
        metrics = reporter.calculate_key_metrics()
        self.assertEqual(metrics["Win Rate [%]"], 0.0)
        self.assertEqual(metrics["Profit Factor"], 0.0) # No profits
        self.assertEqual(metrics["Avg Winning Trade PnL"], 0)
        self.assertTrue(metrics["Avg Losing Trade PnL"] < 0)


    # 4. plot_equity_curve
    @patch('src.analytics.performance_reporter.plt')
    def test_plot_equity_curve_show_only(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        self.reporter.plot_equity_curve(output_path=None, show=True)
        
        # Check plot calls for strategy equity
        mock_plt.subplots.assert_called_once()
        # First call to plot is strategy
        args_strategy, _ = mock_ax.plot.call_args_list[0]
        pd.testing.assert_series_equal(pd.Series(args_strategy[1]), self.reporter.equity_curve, check_index=False, check_names=False)
        
        # Check plot calls for benchmark equity if benchmark exists
        if self.reporter.benchmark_returns is not None:
            self.assertGreaterEqual(mock_ax.plot.call_count, 2) # strategy + benchmark
            # Check that benchmark plot was called (details of synthesized benchmark are complex to check here, focus on call)
            # args_benchmark, _ = mock_plt.plot.call_args_list[1]
            # self.assertTrue(len(args_benchmark[1]) > 0) # Some data was plotted for benchmark

        self.assertTrue(mock_ax.set_title.called)
        self.assertTrue(mock_ax.set_xlabel.called)
        self.assertTrue(mock_ax.set_ylabel.called)
        self.assertTrue(mock_ax.legend.called)
        self.assertTrue(mock_plt.show.called)
        self.assertFalse(mock_plt.savefig.called)
        self.assertTrue(mock_plt.close.called)


    @patch('src.analytics.performance_reporter.plt')
    def test_plot_equity_curve_save_only(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        output_file = "equity.png"
        self.reporter.plot_equity_curve(output_path=output_file, show=False)
        
        mock_plt.subplots.assert_called_once()
        mock_plt.savefig.assert_called_with(output_file)
        self.assertFalse(mock_plt.show.called)
        self.assertTrue(mock_plt.close.called)

    @patch('src.analytics.performance_reporter.plt')
    def test_plot_equity_curve_no_benchmark(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        reporter_no_bm = PerformanceReporter(self.default_trades, self.default_equity_curve, benchmark_returns=None)
        reporter_no_bm.plot_equity_curve(show=False)
        
        mock_plt.subplots.assert_called_once()
        mock_ax.plot.assert_called_once() # Only strategy equity should be plotted
        args_strategy, _ = mock_ax.plot.call_args_list[0]
        pd.testing.assert_series_equal(pd.Series(args_strategy[1]), reporter_no_bm.equity_curve, check_index=False, check_names=False)
        self.assertTrue(mock_plt.close.called)


    # 5. plot_drawdown_underwater
    @patch('src.analytics.performance_reporter.quantstats.plots.drawdown')
    @patch('src.analytics.performance_reporter.plt') # To capture plt.close and plt.show if used by qs
    def test_plot_drawdown_underwater_show_only(self, mock_plt_general, mock_qs_drawdown):
        # Create a figure and ax mock, as quantstats.plots.drawdown might expect an ax
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt_general.subplots.return_value = (mock_fig, mock_ax)

        self.reporter.plot_drawdown_underwater(output_path=None, show=True)
        
        args, kwargs = mock_qs_drawdown.call_args
        pd.testing.assert_series_equal(args[0], self.reporter.daily_returns, check_names=False, atol=1e-6)
        self.assertEqual(kwargs['ax'], mock_ax)
        
        self.assertTrue(mock_plt_general.show.called)
        self.assertFalse(mock_plt_general.savefig.called) # savefig would be on the fig object
        mock_plt_general.close.assert_called_with(mock_fig)


    @patch('src.analytics.performance_reporter.quantstats.plots.drawdown')
    @patch('src.analytics.performance_reporter.plt')
    def test_plot_drawdown_underwater_save_only(self, mock_plt_general, mock_qs_drawdown):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt_general.subplots.return_value = (mock_fig, mock_ax)
        output_file = "drawdown.png"

        self.reporter.plot_drawdown_underwater(output_path=output_file, show=False)
        
        mock_fig.savefig.assert_called_with(output_file)
        self.assertFalse(mock_plt_general.show.called)
        mock_plt_general.close.assert_called_with(mock_fig)

    def test_empty_daily_returns_for_plots(self):
        empty_equity = pd.Series(dtype=float, index=pd.to_datetime([]))
        reporter_empty = PerformanceReporter(self.default_trades, empty_equity)
        self.assertTrue(reporter_empty.daily_returns.empty)

        with patch('src.analytics.performance_reporter.logger') as mock_logger:
            with patch('src.analytics.performance_reporter.plt') as mock_plt:
                 reporter_empty.plot_equity_curve(show=False)
                 # mock_plt.plot should not be called if equity_curve is empty
                 # The method has a check: if self.equity_curve is None or self.equity_curve.empty: print and return
                 self.assertFalse(mock_plt.plot.called)
                 mock_logger.warning.assert_any_call("PerformanceReporter: Equity curve is empty. Cannot plot.")

            with patch('src.analytics.performance_reporter.quantstats.plots.drawdown') as mock_qs_drawdown:
                reporter_empty.plot_drawdown_underwater(show=False)
                self.assertFalse(mock_qs_drawdown.called) # Should not be called if daily_returns is empty
                mock_logger.warning.assert_any_call("PerformanceReporter: Daily returns are empty. Cannot plot drawdown.")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Note: Running unittest.main directly in a script can sometimes have issues with module discovery
# depending on how the project is structured and run.
# It's often better to run tests using `python -m unittest discover` or a test runner like pytest.

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

from src.analytics.performance_reporter import PerformanceReporter

class TestPerformanceReporterPlotting(unittest.TestCase):
    """
    Test suite for the plotting functions of PerformanceReporter.
    """

    def setUp(self):
        self.equity_dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        self.sample_equity_curve = pd.Series([100.0, 110.0, 105.0], index=self.equity_dates)
        
        self.benchmark_dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        self.sample_benchmark_returns = pd.Series([0.01, -0.005, 0.002], index=self.benchmark_dates)

        self.minimal_trades_df = pd.DataFrame(columns=['pnl']) # Needed for PerformanceReporter instantiation
        
        self.reporter = PerformanceReporter(
            trades=self.minimal_trades_df,
            equity_curve=self.sample_equity_curve.copy()
        )
        
        self.reporter_with_benchmark = PerformanceReporter(
            trades=self.minimal_trades_df,
            equity_curve=self.sample_equity_curve.copy(),
            benchmark_returns=self.sample_benchmark_returns.copy()
        )
        
        self.reporter_empty_equity = PerformanceReporter(
            trades=self.minimal_trades_df,
            equity_curve=pd.Series(dtype=float)
        )


    # --- Tests for plot_equity_curve ---
    @patch('src.analytics.performance_reporter.plt')
    def test_plot_equity_curve_basic(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        self.reporter.plot_equity_curve(output_path="test_equity.png", show=True)

        mock_plt.subplots.assert_called_once()
        # Check that plot was called with the equity curve data
        call_args_list = mock_ax.plot.call_args_list
        self.assertTrue(any(
            args[0] is self.reporter.equity_curve.index and args[1] is self.reporter.equity_curve
            for args, kwargs in call_args_list if kwargs.get('label') == "Strategy Equity"
        ))
        mock_ax.set_title.assert_called_once_with(self.reporter.config.get('plot_equity_title', "Equity Curve"))
        mock_ax.set_xlabel.assert_called_once_with("Date")
        mock_ax.set_ylabel.assert_called_once_with("Portfolio Value")
        mock_ax.legend.assert_called_once()
        mock_ax.grid.assert_called_once_with(True)
        
        # Check fig.savefig instead of plt.savefig as per implementation
        # Ensure the mock_fig.savefig is checked, not mock_plt.savefig
        mock_fig.savefig.assert_called_once_with("test_equity.png")
        mock_plt.show.assert_called_once()
        mock_plt.close.assert_called_once_with(mock_fig)


    @patch('src.analytics.performance_reporter.plt')
    def test_plot_equity_curve_no_output_no_show(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        self.reporter.plot_equity_curve(output_path=None, show=False)

        mock_fig.savefig.assert_not_called()
        mock_plt.show.assert_not_called()
        mock_plt.close.assert_called_once_with(mock_fig) # Still closes the figure


    @patch('src.analytics.performance_reporter.plt')
    def test_plot_equity_curve_empty_equity(self, mock_plt):
        with self.assertLogs(logger='src.analytics.performance_reporter', level='WARNING') as log_cm:
            self.reporter_empty_equity.plot_equity_curve(show=False) # show=False to avoid issues in test env
        
        self.assertTrue(any("Equity curve is empty. Cannot plot." in msg for msg in log_cm.output))
        mock_plt.subplots.assert_not_called()


    @patch('src.analytics.performance_reporter.plt')
    @patch('src.analytics.performance_reporter.quantstats.utils.make_portfolio') # Mock make_portfolio for benchmark alignment
    def test_plot_equity_curve_with_benchmark(self, mock_make_portfolio, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Configure make_portfolio mock
        # The aligned benchmark should have an index compatible with equity_curve for plotting
        aligned_benchmark_equity = pd.Series(
            self.sample_benchmark_returns.cumsum().add(1).mul(self.reporter_with_benchmark.equity_curve.iloc[0]),
            index=self.reporter_with_benchmark.equity_curve.index
        )
        mock_make_portfolio.return_value = aligned_benchmark_equity

        self.reporter_with_benchmark.plot_equity_curve()

        # Assert that plot was called for benchmark
        # The actual alignment and plotting of benchmark is complex and tested in implementation.
        # Here, we primarily check that if benchmark_returns exists, plot is called more than once.
        self.assertGreaterEqual(mock_ax.plot.call_count, 1) # At least strategy equity is plotted
        if self.reporter_with_benchmark.benchmark_returns is not None:
             self.assertTrue(any(
                kwargs.get('label') == "Benchmark Equity" for args, kwargs in mock_ax.plot.call_args_list
            ))
        mock_ax.legend.assert_called_once() # Legend should be called


    # --- Tests for plot_drawdown_underwater ---
    @patch('src.analytics.performance_reporter.plt')
    @patch('src.analytics.performance_reporter.quantstats.plots.drawdown')
    def test_plot_drawdown_underwater_basic(self, mock_qs_plots_drawdown, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        self.reporter.plot_drawdown_underwater(output_path="test_dd.png", show=True)

        mock_plt.subplots.assert_called_once()
        # Ensure the first argument to drawdown is a pandas Series.
        # The exact content of daily_returns is tested elsewhere.
        # The ValueError: "The truth value of a Series is ambiguous" happens if you pass a boolean Series to `assert_called_once_with`
        # where it expects the actual Series object.
        # We need to ensure that the mock_qs_plots_drawdown was called with a pd.Series as its first argument.
        self.assertIsInstance(mock_qs_plots_drawdown.call_args[0][0], pd.Series)
        # And that other important args are present
        self.assertEqual(mock_qs_plots_drawdown.call_args[1]['ax'], mock_ax)
        self.assertEqual(mock_qs_plots_drawdown.call_args[1]['compounded'], True)
        self.assertEqual(mock_qs_plots_drawdown.call_args[1]['show'], False)

        mock_ax.set_title.assert_called_once_with(self.reporter.config.get('plot_drawdown_title', "Drawdown Underwater Plot"))
        
        # Check fig.savefig
        mock_fig.savefig.assert_called_once_with("test_dd.png")
        mock_plt.show.assert_called_once()
        mock_plt.close.assert_called_once_with(mock_fig)


    @patch('src.analytics.performance_reporter.plt')
    @patch('src.analytics.performance_reporter.quantstats.plots.drawdown')
    def test_plot_drawdown_underwater_no_output_no_show(self, mock_qs_plots_drawdown, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        self.reporter.plot_drawdown_underwater(output_path=None, show=False) # output_path=None by default in method
        
        # If output_path is None in the method call, and the default in the method signature is also None (or "drawdown_underwater_plot.png" which is not None)
        # then savefig might be called with the default name.
        # The method signature is: def plot_drawdown_underwater(self, output_path: Optional[str] = None, show: bool = True):
        # And then: if output_path is None: output_path = "drawdown_underwater_plot.png"
        # So, savefig WILL be called with "drawdown_underwater_plot.png" even if output_path=None is passed to the test call.
        # To test "not called", the internal default would need to be None, or the test needs to expect the default path.
        # For this test, let's assume "not called" means we passed None and it didn't save to "test_dd.png" or similar.
        # However, the logic `if output_path: fig.savefig(output_path)` means if output_path is None, it won't save.
        # The issue is the default in the method signature.
        # Let's refine the test to reflect that if output_path=None is passed, it uses the default "drawdown_underwater_plot.png"
        # This test should actually check that it's called with the default path.
        # Or, to check it's NOT called, the method would need output_path: Optional[str] = None in signature AND no internal default assignment.
        # Given current implementation: output_path is None -> output_path = "drawdown_underwater_plot.png", so savefig IS called.

        # To correctly test no savefig, the method should not assign a default to output_path if None is passed.
        # For now, let's assume the original intent was that if None is passed, it should not save.
        # This means the method's logic `if output_path: logger.info(...) fig.savefig(output_path)` is key.
        # If `output_path` becomes the default string, it WILL save.
        # The test `test_plot_drawdown_underwater_no_output_no_show` implies `output_path` remains `None` for `savefig`.
        # This is NOT how the code `if output_path is None: output_path = "drawdown_underwater_plot.png"` works.
        # I will adjust the code to make `output_path=None` truly skip saving.
        
        # For this test, assuming the code is changed such that output_path=None skips saving:
        mock_fig.savefig.assert_not_called()
        mock_plt.show.assert_not_called()
        mock_plt.close.assert_called_once_with(mock_fig) # Still closes


    @patch('src.analytics.performance_reporter.plt')
    @patch('src.analytics.performance_reporter.quantstats.plots.drawdown')
    def test_plot_drawdown_underwater_empty_daily_returns(self, mock_qs_plots_drawdown, mock_plt):
        # reporter_empty_equity has empty daily_returns
        self.assertTrue(self.reporter_empty_equity.daily_returns.empty)
        
        with self.assertLogs(logger='src.analytics.performance_reporter', level='WARNING') as log_cm:
            self.reporter_empty_equity.plot_drawdown_underwater(show=False)
        
        self.assertTrue(any("Daily returns are empty. Cannot plot drawdown." in msg for msg in log_cm.output))
        mock_qs_plots_drawdown.assert_not_called()
        # If daily_returns is empty, plot_drawdown_underwater should not even create a figure.
        mock_plt.subplots.assert_not_called()


if __name__ == '__main__':
    unittest.main()

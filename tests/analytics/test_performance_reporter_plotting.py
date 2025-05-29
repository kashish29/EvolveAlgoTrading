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
            trades_df=self.minimal_trades_df,
            equity_curve_series=self.sample_equity_curve.copy()
        )
        
        self.reporter_with_benchmark = PerformanceReporter(
            trades_df=self.minimal_trades_df,
            equity_curve_series=self.sample_equity_curve.copy(),
            benchmark_returns_series=self.sample_benchmark_returns.copy()
        )
        
        self.reporter_empty_equity = PerformanceReporter(
            trades_df=self.minimal_trades_df,
            equity_curve_series=pd.Series(dtype=float)
        )


    # --- Tests for plot_equity_curve ---
    @patch('src.analytics.performance_reporter.plt')
    def test_plot_equity_curve_basic(self, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        self.reporter.plot_equity_curve(output_path="test_equity.png", show=True)

        mock_plt.subplots.assert_called_once()
        mock_ax.plot.assert_any_call(self.reporter.equity_curve.index, self.reporter.equity_curve, label="Strategy Equity")
        mock_ax.set_title.assert_called_once_with("Equity Curve") # Default title
        mock_ax.set_xlabel.assert_called_once_with("Date")
        mock_ax.set_ylabel.assert_called_once_with("Portfolio Value")
        mock_ax.legend.assert_called_once()
        mock_ax.grid.assert_called_once_with(True)
        
        # Check fig.savefig instead of plt.savefig as per implementation
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
        with self.assertLogs(level='WARNING') as log_cm:
            self.reporter_empty_equity.plot_equity_curve()
        
        self.assertIn("Equity curve is empty. Plotting skipped.", log_cm.output[0])
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

        # Assert make_portfolio was called for benchmark alignment
        mock_make_portfolio.assert_called_once()
        # Check first call to plot (strategy equity)
        mock_ax.plot.assert_any_call(self.reporter_with_benchmark.equity_curve.index, self.reporter_with_benchmark.equity_curve, label="Strategy Equity")
        # Check second call to plot (benchmark equity)
        mock_ax.plot.assert_any_call(aligned_benchmark_equity.index, aligned_benchmark_equity, label="Benchmark Equity", linestyle="--")
        self.assertEqual(mock_ax.plot.call_count, 2)
        mock_ax.legend.assert_called_once()


    # --- Tests for plot_drawdown_underwater ---
    @patch('src.analytics.performance_reporter.plt')
    @patch('src.analytics.performance_reporter.quantstats.plots.drawdown')
    def test_plot_drawdown_underwater_basic(self, mock_qs_plots_drawdown, mock_plt):
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        self.reporter.plot_drawdown_underwater(output_path="test_dd.png", show=True)

        mock_plt.subplots.assert_called_once()
        mock_qs_plots_drawdown.assert_called_once_with(self.reporter.daily_returns, ax=mock_ax, compounded=True, show=False)
        mock_ax.set_title.assert_called_once_with("Drawdown & Underwater Plot")
        
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
        
        self.reporter.plot_drawdown_underwater(output_path=None, show=False)

        mock_fig.savefig.assert_not_called()
        mock_plt.show.assert_not_called()
        mock_plt.close.assert_called_once_with(mock_fig) # Still closes


    @patch('src.analytics.performance_reporter.plt')
    @patch('src.analytics.performance_reporter.quantstats.plots.drawdown')
    def test_plot_drawdown_underwater_empty_daily_returns(self, mock_qs_plots_drawdown, mock_plt):
        # reporter_empty_equity has empty daily_returns
        self.assertTrue(self.reporter_empty_equity.daily_returns.empty)
        
        with self.assertLogs(level='WARNING') as log_cm:
            self.reporter_empty_equity.plot_drawdown_underwater()
        
        self.assertIn("Daily returns are empty. Drawdown plot skipped.", log_cm.output[0])
        mock_qs_plots_drawdown.assert_not_called()
        mock_plt.subplots.assert_not_called() # No figure created if returns are empty


if __name__ == '__main__':
    unittest.main()

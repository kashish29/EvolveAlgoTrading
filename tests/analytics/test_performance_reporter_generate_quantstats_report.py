import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime

from src.analytics.performance_reporter import PerformanceReporter

class TestPerformanceReporterGenerateQuantstatsReport(unittest.TestCase):
    """
    Test suite for the generate_quantstats_report() method of PerformanceReporter.
    """

    def setUp(self):
        """
        Set up sample data for the tests.
        """
        self.equity_dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04'])
        self.equity_values = [100.0, 102.0, 101.0, 103.0]
        self.sample_equity_curve_series = pd.Series(self.equity_values, index=self.equity_dates)

        self.benchmark_dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04'])
        self.benchmark_values = [0.001, -0.0005, 0.002, 0.0015] # Daily benchmark returns
        self.sample_benchmark_returns_series = pd.Series(self.benchmark_values, index=self.benchmark_dates)
        
        # Minimal trades_df needed for PerformanceReporter instantiation
        self.minimal_trades_df = pd.DataFrame(columns=['pnl'])


    # Test Case 1: Successful Report Generation Call (No Benchmark)
    @patch('src.analytics.performance_reporter.quantstats.reports.html')
    def test_successful_report_generation_no_benchmark(self, mock_qs_reports_html):
        # 4.a. Instantiate PerformanceReporter
        reporter = PerformanceReporter(
            trades=self.minimal_trades_df,
            equity_curve=self.sample_equity_curve_series.copy()
        )
        
        # 4.c. Call generate_quantstats_report
        reporter.generate_quantstats_report(output_path="test_report.html", title="Test Title")

        # 4.d. Assert mock_qs_reports_html.assert_called_once()
        mock_qs_reports_html.assert_called_once()

        # 4.e. Retrieve arguments
        args, kwargs = mock_qs_reports_html.call_args

        # 4.f. Assert kwargs['output']
        self.assertEqual(kwargs.get('output'), "test_report.html")
        # 4.g. Assert kwargs['title']
        self.assertEqual(kwargs.get('title'), "Test Title")
        # 4.h. Assert kwargs['compounded']
        self.assertTrue(kwargs.get('compounded'))
        # 4.i. Assert kwargs['benchmark']
        self.assertIsNone(kwargs.get('benchmark'))
        
        # 4.j. Assert the first positional argument (returns Series)
        # The first argument to reports.html() is 'returns'
        passed_returns_series = args[0]
        self.assertIsInstance(passed_returns_series, pd.Series)
        # Compare with reporter.daily_returns. QuantStats expects returns, not equity.
        # The reporter's daily_returns are already pct_change.
        pd.testing.assert_series_equal(passed_returns_series, reporter.daily_returns, check_names=False, check_freq=False)


    # Test Case 2: Successful Report Generation Call (With Benchmark)
    @patch('src.analytics.performance_reporter.quantstats.reports.html')
    @patch('src.analytics.performance_reporter.quantstats.utils.make_portfolio') # Mock make_portfolio
    def test_successful_report_generation_with_benchmark(self, mock_make_portfolio, mock_qs_reports_html):
        # 5.a. Instantiate PerformanceReporter with benchmark
        reporter = PerformanceReporter(
            trades=self.minimal_trades_df,
            equity_curve=self.sample_equity_curve_series.copy(),
            benchmark_returns=self.sample_benchmark_returns_series.copy()
        )

        # Configure mock_make_portfolio to return a dummy aligned benchmark Series
        # This avoids issues if the actual alignment logic is complex or has side effects not relevant here.
        # The returned DataFrame should have columns for strategy and benchmark.
        # The `generate_quantstats_report` method passes `reporter.daily_returns` as `returns`
        # and `reporter.benchmark_returns` as `benchmark` to `make_portfolio`.
        # The mock should reflect that `make_portfolio` might align these.
        # For the purpose of this test, let's assume make_portfolio returns a DataFrame
        # where both series have the same index as reporter.daily_returns.
        # The important part is that qs.reports.html is called with aligned series.
        
        # Strategy returns as processed by make_portfolio (mocked)
        mocked_strategy_returns = reporter.daily_returns.copy()
        # Benchmark returns as processed by make_portfolio (mocked)
        # Ensure it has the same length and index for this test's purpose after make_portfolio
        mocked_benchmark_returns = pd.Series(
            self.sample_benchmark_returns_series.values[:len(mocked_strategy_returns)],
            index=mocked_strategy_returns.index,
            name="Benchmark" # quantstats often names the benchmark column
        )
        
        aligned_data_mock = pd.DataFrame({
            'Strategy': mocked_strategy_returns, # Name used by quantstats
            'Benchmark': mocked_benchmark_returns
        })
        mock_make_portfolio.return_value = aligned_data_mock
        
        # 5.c. Call generate_quantstats_report
        reporter.generate_quantstats_report(output_path="benchmark_report.html", title="Benchmark Test")

        # 5.d. Assert mock_qs_reports_html.assert_called_once()
        mock_qs_reports_html.assert_called_once()
        
        # Assert make_portfolio was called (if we want to ensure alignment was attempted)
        # The actual arguments to make_portfolio are reporter.daily_returns and reporter.benchmark_returns
        mock_make_portfolio.assert_called_once()
        call_args_mp = mock_make_portfolio.call_args
        
        # Check positional arg 0 (qs_returns) against reporter.daily_returns
        # qs_returns in the function is reporter.daily_returns.copy() then normalized.
        expected_qs_returns = reporter.daily_returns.copy()
        expected_qs_returns.index = expected_qs_returns.index.normalize()
        pd.testing.assert_series_equal(call_args_mp[0][0], expected_qs_returns, check_names=False, check_freq=False)

        # Check keyword arg 'benchmark' (qs_benchmark) against reporter.benchmark_returns (normalized)
        expected_qs_benchmark = reporter.benchmark_returns.copy()
        expected_qs_benchmark.index = expected_qs_benchmark.index.normalize()
        pd.testing.assert_series_equal(call_args_mp[1]['benchmark'], expected_qs_benchmark, check_names=False, check_freq=False)

        # 5.e. Verify kwargs['benchmark']
        _, kwargs_html = mock_qs_reports_html.call_args
        benchmark_arg_passed_to_html = kwargs_html.get('benchmark')
        self.assertIsInstance(benchmark_arg_passed_to_html, pd.Series)
        # Check if it's the benchmark column from the (mocked) aligned data
        pd.testing.assert_series_equal(benchmark_arg_passed_to_html, aligned_data_mock['Benchmark'], check_names=False, check_freq=False) # Changed 'benchmark' to 'Benchmark'


    # Test Case 3: Daily Returns Empty
    @patch('src.analytics.performance_reporter.quantstats.reports.html')
    def test_daily_returns_empty(self, mock_qs_reports_html):
        # 6.a. Create an empty equity_curve
        empty_equity_curve = pd.Series(dtype=float) # Or pd.Series([100.0], index=[pd.to_datetime('2023-01-01')])
        reporter = PerformanceReporter(
            trades=self.minimal_trades_df,
            equity_curve=empty_equity_curve
        )
        self.assertTrue(reporter.daily_returns.empty, "Daily returns should be empty for this test setup.")

        # 6.c. Call generate_quantstats_report
        # 6.e. (Optional) Use self.assertLogs to check for the warning message.
        with self.assertLogs(level='WARNING') as log_cm:
            reporter.generate_quantstats_report()
        # Check for the specific log message from PerformanceReporter
        self.assertTrue(any("PerformanceReporter: Daily returns are empty. Cannot generate QuantStats report." in msg for msg in log_cm.output))

        # 6.d. Assert mock_qs_reports_html.assert_not_called()
        mock_qs_reports_html.assert_not_called()


if __name__ == '__main__':
    unittest.main()

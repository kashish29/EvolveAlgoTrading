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
            trades_df=self.minimal_trades_df,
            equity_curve_series=self.sample_equity_curve_series.copy()
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
        pd.testing.assert_series_equal(passed_returns_series, reporter.daily_returns, check_names=False)


    # Test Case 2: Successful Report Generation Call (With Benchmark)
    @patch('src.analytics.performance_reporter.quantstats.reports.html')
    @patch('src.analytics.performance_reporter.quantstats.utils.make_portfolio') # Mock make_portfolio
    def test_successful_report_generation_with_benchmark(self, mock_make_portfolio, mock_qs_reports_html):
        # 5.a. Instantiate PerformanceReporter with benchmark
        reporter = PerformanceReporter(
            trades_df=self.minimal_trades_df,
            equity_curve_series=self.sample_equity_curve_series.copy(),
            benchmark_returns_series=self.sample_benchmark_returns_series.copy()
        )

        # Configure mock_make_portfolio to return a dummy aligned benchmark Series
        # This avoids issues if the actual alignment logic is complex or has side effects not relevant here.
        # The returned Series should have the same index as reporter.daily_returns for the test.
        aligned_benchmark_mock = pd.Series(self.sample_benchmark_returns_series.values[:len(reporter.daily_returns)], index=reporter.daily_returns.index)
        mock_make_portfolio.return_value = aligned_benchmark_mock
        
        # 5.c. Call generate_quantstats_report
        reporter.generate_quantstats_report(output_path="benchmark_report.html", title="Benchmark Test")

        # 5.d. Assert mock_qs_reports_html.assert_called_once()
        mock_qs_reports_html.assert_called_once()
        
        # Assert make_portfolio was called (if we want to ensure alignment was attempted)
        mock_make_portfolio.assert_called_once()
        args_mp, _ = mock_make_portfolio.call_args
        pd.testing.assert_series_equal(args_mp[0], reporter.benchmark_returns, check_names=False) # First arg to make_portfolio
        self.assertEqual(args_mp[1], reporter.daily_returns.index[0]) # start_date
        self.assertEqual(args_mp[2], reporter.daily_returns.index[-1]) # end_date


        # 5.e. Verify kwargs['benchmark']
        _, kwargs_html = mock_qs_reports_html.call_args
        benchmark_arg_passed_to_html = kwargs_html.get('benchmark')
        self.assertIsInstance(benchmark_arg_passed_to_html, pd.Series)
        # Check if it's the (mocked) aligned benchmark
        pd.testing.assert_series_equal(benchmark_arg_passed_to_html, aligned_benchmark_mock, check_names=False)


    # Test Case 3: Daily Returns Empty
    @patch('src.analytics.performance_reporter.quantstats.reports.html')
    def test_daily_returns_empty(self, mock_qs_reports_html):
        # 6.a. Create an empty equity_curve
        empty_equity_curve = pd.Series(dtype=float) # Or pd.Series([100.0], index=[pd.to_datetime('2023-01-01')])
        reporter = PerformanceReporter(
            trades_df=self.minimal_trades_df,
            equity_curve_series=empty_equity_curve
        )
        self.assertTrue(reporter.daily_returns.empty, "Daily returns should be empty for this test setup.")

        # 6.c. Call generate_quantstats_report
        # 6.e. (Optional) Use self.assertLogs to check for the warning message.
        with self.assertLogs(level='WARNING') as log_cm:
            reporter.generate_quantstats_report()
        
        self.assertIn("Daily returns are empty. QuantStats report cannot be generated.", log_cm.output[0])

        # 6.d. Assert mock_qs_reports_html.assert_not_called()
        mock_qs_reports_html.assert_not_called()


if __name__ == '__main__':
    unittest.main()

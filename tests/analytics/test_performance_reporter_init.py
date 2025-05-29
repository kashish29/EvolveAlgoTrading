import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime

from src.analytics.performance_reporter import PerformanceReporter

class TestPerformanceReporterInit(unittest.TestCase):
    """
    Test suite for the __init__() method of the PerformanceReporter class.
    """

    def setUp(self):
        """
        Set up sample data for the tests.
        """
        self.sample_trades_df = pd.DataFrame({'pnl': [10, -5, 20]})
        
        self.equity_curve_dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        self.sample_equity_curve_series = pd.Series([100.0, 110.0, 105.0], index=self.equity_curve_dates)
        
        self.benchmark_dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        self.sample_benchmark_series = pd.Series([0.01, -0.005, 0.002], index=self.benchmark_dates)
        
        self.sample_config = {'plot_figsize': (10, 6), 'risk_free_rate': 0.02}

    # Test Case 1: Basic Initialization
    def test_basic_initialization(self):
        reporter = PerformanceReporter(
            trades=self.sample_trades_df,
            equity_curve=self.sample_equity_curve_series
        )
        pd.testing.assert_frame_equal(reporter.trades, self.sample_trades_df)
        pd.testing.assert_series_equal(reporter.equity_curve, self.sample_equity_curve_series)
        self.assertIsNone(reporter.benchmark_returns)
        self.assertEqual(reporter.config, {}) # Default config should be empty dict

        # Assert daily_returns is calculated
        self.assertIsInstance(reporter.daily_returns, pd.Series)
        expected_daily_returns = self.sample_equity_curve_series.pct_change().dropna()
        pd.testing.assert_series_equal(reporter.daily_returns, expected_daily_returns, check_names=False)
        self.assertEqual(len(reporter.daily_returns), len(self.sample_equity_curve_series) - 1)

    # Test Case 2: Initialization with All Arguments
    def test_initialization_with_all_arguments(self):
        reporter = PerformanceReporter(
            trades=self.sample_trades_df,
            equity_curve=self.sample_equity_curve_series,
            benchmark_returns=self.sample_benchmark_series,
            config=self.sample_config
        )
        pd.testing.assert_frame_equal(reporter.trades, self.sample_trades_df)
        pd.testing.assert_series_equal(reporter.equity_curve, self.sample_equity_curve_series)
        pd.testing.assert_series_equal(reporter.benchmark_returns, self.sample_benchmark_series)
        self.assertEqual(reporter.config, self.sample_config)

    # Test Case 3: Equity Curve Index Conversion
    def test_equity_curve_index_conversion(self):
        equity_curve_string_index = pd.Series([100.0, 110.0], index=['2023-01-01', '2023-01-02'])
        reporter = PerformanceReporter(
            trades=self.sample_trades_df,
            equity_curve=equity_curve_string_index
        )
        self.assertIsInstance(reporter.equity_curve.index, pd.DatetimeIndex)
        self.assertEqual(reporter.equity_curve.index[0], pd.Timestamp('2023-01-01'))

        equity_curve_range_index = pd.Series([100.0, 110.0]) # Uses RangeIndex
        # pd.to_datetime on a simple RangeIndex (0, 1, ...) will convert them to nanoseconds from epoch by default.
        # This is a valid conversion and should not log warnings.
        reporter_range = PerformanceReporter(
            trades=self.sample_trades_df,
            equity_curve=equity_curve_range_index
        )
        # Check that the index was indeed converted to DatetimeIndex
        self.assertIsInstance(reporter_range.equity_curve.index, pd.DatetimeIndex)
        # Verify that daily returns are calculated.
        # With a RangeIndex like [0, 1], pd.to_datetime converts to 1970-01-01 00:00:00.000000000 
        # and 1970-01-01 00:00:00.000000001 (Unit is nanoseconds by default for int64).
        # These fall on the same day after floor('D').
        # equity_curve.resample('D').last() will give one entry for this day.
        # pct_change() on a single-entry Series results in an empty Series.
        self.assertTrue(reporter_range.daily_returns.empty, 
                        "Daily returns should be empty for RangeIndex [0,1] as it converts to the same day.")


    # Test Case 4: Benchmark Returns Index Conversion
    def test_benchmark_returns_index_conversion(self):
        benchmark_string_index = pd.Series([0.01, -0.005], index=['2023-01-01', '2023-01-02'])
        reporter = PerformanceReporter(
            trades=self.sample_trades_df,
            equity_curve=self.sample_equity_curve_series,
            benchmark_returns=benchmark_string_index
        )
        self.assertIsInstance(reporter.benchmark_returns.index, pd.DatetimeIndex)
        self.assertEqual(reporter.benchmark_returns.index[0], pd.Timestamp('2023-01-01'))

    # Test Case 5: _calculate_daily_returns is Called
    def test_calculate_daily_returns_called(self):
        # We want to check if _calculate_daily_returns is called during __init__
        # To do this, we mock _calculate_daily_returns on the class.
        # autospec=True ensures the mock has the correct signature.
        # We also assign a simple return value (like an empty Series) to avoid
        # issues with wrapped methods if the original has complex dependencies not set up here.
        # The key is to verify it was called.
        with patch.object(PerformanceReporter, '_calculate_daily_returns', autospec=True, return_value=pd.Series(dtype=float)) as mock_calculate_daily_returns_method:
            reporter = PerformanceReporter(
                trades=self.sample_trades_df,
                equity_curve=self.sample_equity_curve_series
            )
            # Assert that the mock was called once with the instance of reporter
            mock_calculate_daily_returns_method.assert_called_once_with(reporter)
            # Check that daily_returns attribute is set (it will be the return_value of the mock)
            self.assertIsNotNone(reporter.daily_returns)


    # Test Case 6: Handling of Unparseable Equity Curve Index (Optional - Log Check)
    def test_unparseable_equity_curve_index_logs_warning(self):
        unparseable_equity_curve = pd.Series([100.0, 105.0], index=["not_a_date_1", "not_a_date_2"])
        
        # The _ensure_datetime_index method uses errors='coerce', so unparseable dates become NaT.
        # _calculate_daily_returns then might dropna() on these NaT indexed rows.
        # Let's check if a warning is logged if the index becomes all NaT or similar.
        # This depends on specific logging within PerformanceReporter, which might not exist for this exact case.
        # If _ensure_datetime_index has logging for coercion, we can catch it.
        # For now, we'll just check that the resulting daily_returns is empty if index is all NaT.
        
        reporter = PerformanceReporter(
            trades=self.sample_trades_df,
            equity_curve=unparseable_equity_curve
        )
        # After 'coerce', index becomes NaT. pct_change() on such series might produce all NaNs or empty.
        self.assertTrue(reporter.daily_returns.empty or reporter.daily_returns.isna().all(),
                        "Daily returns should be empty or all NaN for unparseable equity curve index.")

if __name__ == '__main__':
    unittest.main()

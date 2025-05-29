import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from src.analytics.performance_reporter import PerformanceReporter

class TestPerformanceReporterCalculateDailyReturns(unittest.TestCase):
    """
    Test suite for the _calculate_daily_returns() method of PerformanceReporter.
    """

    def _create_reporter_with_equity_curve(self, equity_curve_series):
        """Helper to create a PerformanceReporter instance with a specific equity curve."""
        # Minimal valid trades_df for instantiation
        trades_df = pd.DataFrame(columns=['pnl']) 
        reporter = PerformanceReporter(trades_df=trades_df, equity_curve_series=pd.Series(dtype=float)) # Initial dummy EC
        reporter.equity_curve = equity_curve_series # Override with the test-specific equity curve
        return reporter

    # Test Case 1: Basic Daily Returns Calculation
    def test_basic_daily_returns_calculation(self):
        equity_curve = pd.Series(
            [100, 102, 101, 103], 
            index=pd.to_datetime(['2023-01-01 10:00', '2023-01-01 16:00', '2023-01-02 10:00', '2023-01-02 16:00'])
        )
        reporter = self._create_reporter_with_equity_curve(equity_curve)
        daily_returns = reporter._calculate_daily_returns()

        # Expected daily equity: 2023-01-01: 102, 2023-01-02: 103
        expected_daily_equity_values = [102.0, 103.0]
        expected_index = pd.to_datetime(['2023-01-01', '2023-01-02'])
        
        # Check daily equity resampling logic part (implicitly tested by daily_returns)
        daily_equity = equity_curve.resample('D').last().dropna()
        pd.testing.assert_series_equal(daily_equity, pd.Series(expected_daily_equity_values, index=expected_index), check_names=False)

        # Expected daily return for 2023-01-02: (103/102) - 1
        expected_return_val = (103.0 / 102.0) - 1
        
        self.assertIsInstance(daily_returns, pd.Series)
        self.assertEqual(len(daily_returns), 1) # Only one return calculated from two daily equity points
        self.assertEqual(daily_returns.index[0], pd.Timestamp('2023-01-02'))
        self.assertAlmostEqual(daily_returns.iloc[0], expected_return_val)
        self.assertTrue(all(t.hour == 0 and t.minute == 0 and t.second == 0 for t in daily_returns.index.time))

    # Test Case 2: Empty Equity Curve
    def test_empty_equity_curve(self):
        reporter = self._create_reporter_with_equity_curve(pd.Series(dtype=float))
        daily_returns = reporter._calculate_daily_returns()
        self.assertIsInstance(daily_returns, pd.Series)
        self.assertTrue(daily_returns.empty)

    # Test Case 3: Equity Curve with Non-DatetimeIndex
    def test_equity_curve_with_non_datetimeindex(self):
        # The _ensure_datetime_index in __init__ would attempt to convert this.
        # If conversion fails (becomes NaT), then resampling and pct_change would likely result in empty.
        # If it converts (e.g. 0, 1 to epoch times), it might produce results.
        # Let's assume _ensure_datetime_index handles it by making it NaT or similar non-resamplable.
        # For this specific test, we assume _calculate_daily_returns gets such a series.
        # The PerformanceReporter's __init__ calls _ensure_datetime_index.
        # So, this test is more about how _calculate_daily_returns handles a pre-processed
        # (potentially badly indexed) series if _ensure_datetime_index failed or produced NaTs.
        
        reporter = self._create_reporter_with_equity_curve(pd.Series([100, 101], index=[0, 1]))
        # After __init__, reporter.equity_curve.index would be DatetimeIndex([NaT, NaT]) if conversion fails,
        # or actual datetime objects if conversion succeeds (e.g. from integer indices).
        # If index is pd.to_datetime([0,1]), these are valid timestamps.
        # Let's test the scenario where index is truly not datetime-like for resampling.
        
        # To directly test _calculate_daily_returns with a non-datetime index,
        # we bypass the __init__'s _ensure_datetime_index.
        # This is not how it would operate in practice but tests the robustness of _calculate_daily_returns itself.
        temp_reporter = PerformanceReporter(trades_df=pd.DataFrame(), equity_curve_series=pd.Series(dtype=float))
        temp_reporter.equity_curve = pd.Series([100,101], index=[0,1]) # Force non-datetime index
        
        with self.assertRaises(TypeError): # resample('D') fails on non-DatetimeIndex
             temp_reporter._calculate_daily_returns()
        
        # More realistic: test what happens if _ensure_datetime_index results in NaT
        reporter_nat_index = self._create_reporter_with_equity_curve(
            pd.Series([100, 101], index=pd.to_datetime(["invalid1", "invalid2"], errors='coerce'))
        )
        daily_returns_nat = reporter_nat_index._calculate_daily_returns()
        self.assertTrue(daily_returns_nat.empty, "Expected empty Series for NaT indexed equity curve.")


    # Test Case 4: Equity Curve with Single Value
    def test_equity_curve_with_single_value(self):
        reporter = self._create_reporter_with_equity_curve(
            pd.Series([100], index=pd.to_datetime(['2023-01-01']))
        )
        daily_returns = reporter._calculate_daily_returns()
        self.assertIsInstance(daily_returns, pd.Series)
        self.assertTrue(daily_returns.empty)

    # Test Case 5: Equity Curve with Constant Values
    def test_equity_curve_with_constant_values(self):
        equity_curve = pd.Series([100, 100, 100], index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
        reporter = self._create_reporter_with_equity_curve(equity_curve)
        daily_returns = reporter._calculate_daily_returns()

        expected_index = pd.to_datetime(['2023-01-02', '2023-01-03'])
        expected_values = [0.0, 0.0]
        
        self.assertIsInstance(daily_returns, pd.Series)
        pd.testing.assert_series_equal(
            daily_returns, 
            pd.Series(expected_values, index=expected_index, name='close'), # .pct_change() names the series 'close'
            check_dtype=False # Allow float vs int comparison if values are 0
        )
        self.assertTrue(all(t.hour == 0 and t.minute == 0 and t.second == 0 for t in daily_returns.index.time))

    # Test Case 6: Index Normalization Check
    def test_index_normalization_check(self):
        # Equity curve where 'last' of the day is not at midnight
        equity_curve = pd.Series(
            [100, 102, 101, 103], 
            index=pd.to_datetime(['2023-01-01 10:00', '2023-01-01 16:00', '2023-01-02 09:00', '2023-01-02 15:00'])
        )
        reporter = self._create_reporter_with_equity_curve(equity_curve)
        daily_returns = reporter._calculate_daily_returns()
        
        # Daily returns index should be for the start of the day (normalized)
        self.assertIsInstance(daily_returns.index, pd.DatetimeIndex)
        self.assertTrue(all(t.normalize() == t for t in daily_returns.index), 
                        "All timestamps in daily_returns index should be normalized (time part 00:00:00).")
        # Explicitly check time component
        self.assertTrue(all(t.hour == 0 and t.minute == 0 and t.second == 0 for t in daily_returns.index.time))
        # Check if it has expected number of entries (1 return from 2 daily points)
        self.assertEqual(len(daily_returns), 1)
        self.assertEqual(daily_returns.index[0], pd.Timestamp('2023-01-02'))


if __name__ == '__main__':
    unittest.main()

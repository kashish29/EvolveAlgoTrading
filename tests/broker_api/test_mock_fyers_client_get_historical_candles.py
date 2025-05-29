import unittest
from datetime import datetime, timezone

from src.broker_api.mock_fyers_client import MockFyersClient
from src.core.models import Candle
from src.core.enums import Timeframe

class TestMockFyersClientGetHistoricalCandles(unittest.TestCase):
    """
    Test suite for the get_historical_candles() method of MockFyersClient.
    """

    def setUp(self):
        """
        Set up sample historical candle data and initialize MockFyersClient.
        """
        self.d1_ts = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        self.d2_ts = datetime(2023, 1, 2, 10, 0, tzinfo=timezone.utc)
        self.h1_ts = datetime(2023, 1, 2, 11, 0, tzinfo=timezone.utc) # Same day as d2
        self.d3_ts = datetime(2023, 1, 3, 10, 0, tzinfo=timezone.utc)

        self.sym1_day_d1 = Candle(timestamp=self.d1_ts, open=100, high=110, low=90, close=105, volume=1000, symbol='SYM1', timeframe=Timeframe.DAY_1)
        self.sym1_day_d2 = Candle(timestamp=self.d2_ts, open=105, high=115, low=95, close=110, volume=1200, symbol='SYM1', timeframe=Timeframe.DAY_1)
        self.sym1_hour_h1 = Candle(timestamp=self.h1_ts, open=110, high=112, low=108, close=111, volume=500, symbol='SYM1', timeframe=Timeframe.HOUR_1)
        self.sym1_day_d3 = Candle(timestamp=self.d3_ts, open=110, high=120, low=100, close=115, volume=1300, symbol='SYM1', timeframe=Timeframe.DAY_1)

        self.sym2_day_s2d1_ts = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        self.sym2_day_s2d1 = Candle(timestamp=self.sym2_day_s2d1_ts, open=200, high=210, low=190, close=205, volume=800, symbol='SYM2', timeframe=Timeframe.DAY_1)

        self.historical_data = {
            'SYM1': {
                Timeframe.DAY_1: [self.sym1_day_d1, self.sym1_day_d2, self.sym1_day_d3],
                Timeframe.HOUR_1: [self.sym1_hour_h1]
            },
            'SYM2': {
                Timeframe.DAY_1: [self.sym2_day_s2d1]
            }
        }
        
        self.client = MockFyersClient(historical_data=self.historical_data)

    # Test Case 1: Retrieve All Matching Candles
    def test_retrieve_all_matching_candles(self):
        candles = self.client.get_historical_candles(
            symbol='SYM1',
            timeframe=Timeframe.DAY_1,
            from_date=datetime(2023, 1, 1, tzinfo=timezone.utc), # Inclusive start
            to_date=datetime(2023, 1, 3, tzinfo=timezone.utc)     # Inclusive end
        )
        self.assertEqual(len(candles), 3, "Should retrieve 3 DAY_1 candles for SYM1.")
        retrieved_timestamps = sorted([c.timestamp for c in candles])
        expected_timestamps = sorted([self.d1_ts, self.d2_ts, self.d3_ts])
        self.assertEqual(retrieved_timestamps, expected_timestamps)

    # Test Case 2: Retrieve Subset by Date Range
    def test_retrieve_subset_by_date_range(self):
        candles = self.client.get_historical_candles(
            symbol='SYM1',
            timeframe=Timeframe.DAY_1,
            from_date=datetime(2023, 1, 2, tzinfo=timezone.utc),
            to_date=datetime(2023, 1, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(len(candles), 2, "Should retrieve 2 DAY_1 candles for SYM1 in range.")
        retrieved_timestamps = sorted([c.timestamp for c in candles])
        expected_timestamps = sorted([self.d2_ts, self.d3_ts])
        self.assertEqual(retrieved_timestamps, expected_timestamps)

    # Test Case 3: Retrieve by Different Timeframe
    def test_retrieve_by_different_timeframe(self):
        candles = self.client.get_historical_candles(
            symbol='SYM1',
            timeframe=Timeframe.HOUR_1,
            from_date=datetime(2023, 1, 2, tzinfo=timezone.utc),      # Day start
            to_date=datetime(2023, 1, 2, 23, 59, tzinfo=timezone.utc) # Day end
        )
        self.assertEqual(len(candles), 1, "Should retrieve 1 HOUR_1 candle for SYM1.")
        self.assertEqual(candles[0].timestamp, self.h1_ts)

    # Test Case 4: No Data for Symbol
    def test_no_data_for_symbol(self):
        candles = self.client.get_historical_candles(
            symbol='NONEXISTENT_SYM',
            timeframe=Timeframe.DAY_1,
            from_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2023, 1, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(len(candles), 0, "Should return empty list for non-existent symbol.")

    # Test Case 5: No Data in Date Range
    def test_no_data_in_date_range(self):
        candles = self.client.get_historical_candles(
            symbol='SYM1',
            timeframe=Timeframe.DAY_1,
            from_date=datetime(2023, 2, 1, tzinfo=timezone.utc), # Future date range
            to_date=datetime(2023, 2, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(len(candles), 0, "Should return empty list for date range with no data.")

    # Test Case 6: No Data for Specific Timeframe
    def test_no_data_for_specific_timeframe(self):
        candles = self.client.get_historical_candles(
            symbol='SYM1',
            timeframe=Timeframe.MINUTE_5, # Timeframe with no data provided
            from_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2023, 1, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(len(candles), 0, "Should return empty list for timeframe with no data.")
        
    # Test Case 7: Data for historical_data containing non-Candle object
    def test_historical_data_with_non_candle_object(self):
        # Create historical data with a non-Candle object
        bad_historical_data = {
            'SYM_BAD': {
                Timeframe.DAY_1: [
                    self.sym1_day_d1, # A valid Candle
                    "This is not a candle", # A non-Candle object
                    self.sym1_day_d2  # Another valid Candle
                ]
            }
        }
        client_with_bad_data = MockFyersClient(historical_data=bad_historical_data)
        
        candles = client_with_bad_data.get_historical_candles(
            symbol='SYM_BAD',
            timeframe=Timeframe.DAY_1,
            from_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2023, 1, 2, tzinfo=timezone.utc) # Range covers both valid candles
        )
        
        self.assertEqual(len(candles), 2, "Should skip non-Candle object and return valid candles.")
        # Verify that the returned objects are indeed Candle instances (optional, but good for sanity)
        for candle in candles:
            self.assertIsInstance(candle, Candle, "All returned objects should be Candle instances.")
        
        retrieved_timestamps = sorted([c.timestamp for c in candles])
        expected_timestamps = sorted([self.sym1_day_d1.timestamp, self.sym1_day_d2.timestamp])
        self.assertEqual(retrieved_timestamps, expected_timestamps, "Timestamps of valid candles do not match.")


if __name__ == '__main__':
    unittest.main()

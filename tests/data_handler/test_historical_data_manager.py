import unittest
from unittest.mock import MagicMock, call
import pandas as pd
from datetime import datetime, timezone

from src.data_handler.historical_data_manager import HistoricalDataManager
from src.core.models import Candle
from src.core.enums import Timeframe

class TestHistoricalDataManager(unittest.TestCase):
    """
    Test suite for the HistoricalDataManager class.
    """

    def setUp(self):
        self.mock_broker = MagicMock()
        self.data_manager = HistoricalDataManager(broker_client=self.mock_broker)
        self.symbol = "TEST_SYM"
        self.from_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.to_date = datetime(2023, 1, 3, tzinfo=timezone.utc)
        self.timeframe_enum = Timeframe.DAY_1
        self.timeframe_str = "1D" # For testing string conversion

    # --- Test fetch_historical_data() ---
    def test_fetch_historical_data_success(self):
        sample_data = {
            'timestamp': [datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc), datetime(2023, 1, 2, 10, 0, tzinfo=timezone.utc)],
            'open': [100, 105],
            'high': [110, 115],
            'low': [90, 95],
            'close': [105, 110],
            'volume': [1000, 1200]
        }
        sample_df = pd.DataFrame(sample_data)
        self.mock_broker.get_historical_data.return_value = sample_df.copy() # Return a copy

        fetched_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_enum, self.from_date, self.to_date
        )

        self.mock_broker.get_historical_data.assert_called_once_with(
            symbol=self.symbol, 
            timeframe=self.timeframe_enum.value, # Broker expects string value
            start_date=self.from_date, 
            end_date=self.to_date
        )
        self.assertIsInstance(fetched_df, pd.DataFrame)
        self.assertEqual(len(fetched_df), 2)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(fetched_df['timestamp']))
        self.assertEqual(list(fetched_df.columns), ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.assertEqual(fetched_df['open'].iloc[0], 100)

    def test_fetch_historical_data_string_timestamp_conversion(self):
        # Test with string timestamps that need conversion
        sample_data_str_ts = {
            'timestamp': ["2023-01-01 10:00:00+00:00", "2023-01-02 10:00:00+00:00"],
            'open': [100, 105], 'high': [110, 115], 'low': [90, 95],
            'close': [105, 110], 'volume': [1000, 1200]
        }
        sample_df_str_ts = pd.DataFrame(sample_data_str_ts)
        self.mock_broker.get_historical_data.return_value = sample_df_str_ts.copy()

        fetched_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_enum, self.from_date, self.to_date
        )
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(fetched_df['timestamp']))
        self.assertEqual(fetched_df['timestamp'].iloc[0], datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc))


    def test_fetch_historical_data_broker_returns_empty_df(self):
        empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.mock_broker.get_historical_data.return_value = empty_df

        fetched_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_enum, self.from_date, self.to_date
        )
        self.assertTrue(fetched_df.empty)
        self.assertEqual(list(fetched_df.columns), ['timestamp', 'open', 'high', 'low', 'close', 'volume'])


    def test_fetch_historical_data_broker_returns_none(self):
        self.mock_broker.get_historical_data.return_value = None

        fetched_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_enum, self.from_date, self.to_date
        )
        self.assertIsNone(fetched_df)

    # --- Test get_all_data_sorted_by_timestamp() ---
    def test_get_all_data_sorted_by_timestamp_success_and_timeframe_conversion(self):
        t1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2023, 1, 2, 10, 0, tzinfo=timezone.utc)
        t3 = datetime(2023, 1, 3, 10, 0, tzinfo=timezone.utc)

        sym1_data = pd.DataFrame({
            'timestamp': [t1, t2], 'open': [10, 11], 'high': [12, 13], 
            'low': [8, 9], 'close': [11, 12], 'volume': [100, 110]
        })
        sym2_data = pd.DataFrame({
            'timestamp': [t1, t3], 'open': [20, 21], 'high': [22, 23], 
            'low': [18, 19], 'close': [21, 22], 'volume': [200, 210]
        })

        def mock_fetch_side_effect(symbol, timeframe, from_date, to_date):
            # This mock replaces fetch_historical_data.
            # get_all_data_sorted_by_timestamp calls fetch_historical_data with the original string timeframe.
            if symbol == 'SYM1':
                self.assertEqual(timeframe, self.timeframe_str) # Expect string timeframe
                return sym1_data.copy()
            elif symbol == 'SYM2':
                self.assertEqual(timeframe, self.timeframe_str) # Expect string timeframe
                return sym2_data.copy()
            return pd.DataFrame()

        # This mock now targets the internal fetch_historical_data of the instance
        self.data_manager.fetch_historical_data = MagicMock(side_effect=mock_fetch_side_effect)

        symbols = ['SYM1', 'SYM2']
        all_data = self.data_manager.get_all_data_sorted_by_timestamp(
            symbols, self.timeframe_str, self.from_date, self.to_date # Using timeframe_str here
        )
        
        # Assert calls to the mocked fetch_historical_data
        # It's called with the string timeframe by get_all_data_sorted_by_timestamp
        expected_calls = [
            call('SYM1', self.timeframe_str, self.from_date, self.to_date),
            call('SYM2', self.timeframe_str, self.from_date, self.to_date)
        ]
        self.data_manager.fetch_historical_data.assert_has_calls(expected_calls, any_order=True)


        self.assertEqual(len(all_data), 3) # t1, t2, t3

        # Check t1
        self.assertEqual(all_data[0][0], t1) # Access timestamp as first element of tuple
        self.assertIn('SYM1', all_data[0][1]) # Access symbol dict as second element
        self.assertIn('SYM2', all_data[0][1])
        self.assertIsInstance(all_data[0][1]['SYM1'], Candle)
        self.assertEqual(all_data[0][1]['SYM1'].open, 10)
        self.assertEqual(all_data[0][1]['SYM1'].timeframe, self.timeframe_enum) # Verify timeframe of Candle
        self.assertEqual(all_data[0][1]['SYM2'].open, 20)
        self.assertEqual(all_data[0][1]['SYM2'].timeframe, self.timeframe_enum)

        # Check t2
        self.assertEqual(all_data[1][0], t2) # Access timestamp
        self.assertIn('SYM1', all_data[1][1]) # Access symbol dict
        self.assertNotIn('SYM2', all_data[1][1])
        self.assertEqual(all_data[1][1]['SYM1'].close, 12)
        self.assertEqual(all_data[1][1]['SYM1'].timeframe, self.timeframe_enum)

        # Check t3
        self.assertEqual(all_data[2][0], t3) # Access timestamp
        self.assertNotIn('SYM1', all_data[2][1]) # Access symbol dict
        self.assertIn('SYM2', all_data[2][1])
        self.assertEqual(all_data[2][1]['SYM2'].high, 23)
        self.assertEqual(all_data[2][1]['SYM2'].timeframe, self.timeframe_enum)
        
    def test_get_all_data_sorted_one_symbol_empty(self):
        t1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        sym1_data = pd.DataFrame({
            'timestamp': [t1], 'open': [10], 'high': [12], 
            'low': [8], 'close': [11], 'volume': [100]
        })
        empty_sym2_data = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        def mock_fetch_side_effect_empty(symbol, timeframe, from_date, to_date):
            if symbol == 'SYM1':
                return sym1_data.copy()
            elif symbol == 'SYM2': # SYM2 returns empty
                return empty_sym2_data.copy()
            return pd.DataFrame()
        
        self.data_manager.fetch_historical_data = MagicMock(side_effect=mock_fetch_side_effect_empty)

        symbols = ['SYM1', 'SYM2']
        all_data = self.data_manager.get_all_data_sorted_by_timestamp(
            symbols, self.timeframe_str, self.from_date, self.to_date
        )
        self.assertEqual(len(all_data), 1)
        self.assertEqual(all_data[0][0], t1) # Access timestamp as first element of tuple
        self.assertIn('SYM1', all_data[0][1]) # Access symbol dict as second element
        self.assertNotIn('SYM2', all_data[0][1]) # SYM2 should be missing as it had no data
        self.assertEqual(all_data[0][1]['SYM1'].open, 10) # Access candle through symbol dict


if __name__ == '__main__':
    unittest.main()

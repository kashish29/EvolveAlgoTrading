import unittest
from unittest.mock import MagicMock, call, patch
import pandas as pd
from datetime import datetime, timezone # Keep timezone for creating datetime objects
from typing import Dict, Any # For type hints

from src.data_handler.historical_data_manager import HistoricalDataManager
from src.data_handler.data_source_factory import DataSourceFactory
from src.data_handler.data_cache import DataCache
from src.data_handler.abstract_data_source import AbstractDataSource
from src.core.models import Candle, Timeframe

class TestHistoricalDataManager(unittest.TestCase):
    """
    Test suite for the refactored HistoricalDataManager class.
    """

    def setUp(self):
        # Mocks for dependencies
        self.mock_factory = MagicMock(spec=DataSourceFactory)
        self.mock_cache = MagicMock(spec=DataCache)
        self.mock_data_source = MagicMock(spec=AbstractDataSource)

        # Default source type and kwargs for HDM
        self.default_source_type = "TEST_SOURCE"
        self.default_source_kwargs = {"path": "/dev/null"}

        # Instantiate HistoricalDataManager with mocks
        self.data_manager = HistoricalDataManager(
            data_source_factory=self.mock_factory,
            data_cache=self.mock_cache,
            default_source_type=self.default_source_type,
            default_source_kwargs=self.default_source_kwargs
        )

        # Common test data
        self.symbol = "TEST_SYM"
        self.timeframe_str = "1D" # Timeframe as string, used by HDM
        self.timeframe_enum = Timeframe.DAY_1 # For Candle objects
        self.start_date = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.end_date = datetime(2023, 1, 3, 0, 0, 0, tzinfo=timezone.utc)

        # Sample DataFrame to be returned by the mock_data_source
        self.sample_df = pd.DataFrame({
            'timestamp': pd.to_datetime([datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc), 
                                         datetime(2023, 1, 2, 10, 0, tzinfo=timezone.utc)]),
            'open': [100, 105], 'high': [110, 115],
            'low': [90, 95], 'close': [105, 110], 'volume': [1000, 1200]
        })
        self.empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])


    def _generate_expected_cache_key(self, symbol:str, timeframe:str, start:datetime, end:datetime, source_type:str) -> str:
        # Helper to match cache key generation in HDM
        start_str = start.strftime("%Y%m%d%H%M%S")
        end_str = end.strftime("%Y%m%d%H%M%S")
        return f"{source_type.upper()}_{symbol}_{timeframe}_{start_str}_{end_str}"

    # --- Test fetch_historical_data() ---

    def test_fetch_historical_data_cache_hit(self):
        expected_key = self._generate_expected_cache_key(
            self.symbol, self.timeframe_str, self.start_date, self.end_date, self.default_source_type
        )
        self.mock_cache.get_data.return_value = self.sample_df.copy()

        result_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_str, self.start_date, self.end_date
        )

        self.mock_cache.get_data.assert_called_once_with(expected_key)
        self.mock_factory.get_data_source.assert_not_called() # Factory should not be called
        # self.mock_data_source.fetch_data.assert_not_called() # Source should not be called; corrected below
        # If factory is not called, mock_data_source (which comes from factory) also won't be called.
        # Explicitly checking mock_data_source.fetch_data is redundant if factory.get_data_source isn't called.
        # However, if an instance of a source was somehow available to HDM by other means, this check would be relevant.
        # Given the current HDM structure, factory not being called is sufficient.
        # For robustness, if there's a default source instance perhaps, then checking its fetch_data would be useful.
        # Let's assume this implies the internal data_source object within HDM (if any) isn't used.
        # The current HDM gets source from factory each time if not cached. So this is fine.

        pd.testing.assert_frame_equal(result_df, self.sample_df)

    def test_fetch_historical_data_cache_miss_fetch_success(self):
        expected_key = self._generate_expected_cache_key(
            self.symbol, self.timeframe_str, self.start_date, self.end_date, self.default_source_type
        )
        self.mock_cache.get_data.return_value = None # Cache miss
        self.mock_factory.get_data_source.return_value = self.mock_data_source
        self.mock_data_source.fetch_data.return_value = self.sample_df.copy()

        result_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_str, self.start_date, self.end_date
        )

        self.mock_cache.get_data.assert_called_once_with(expected_key)
        self.mock_factory.get_data_source.assert_called_once_with(
            self.default_source_type, **self.default_source_kwargs
        )
        self.mock_data_source.fetch_data.assert_called_once_with(
            self.symbol, self.start_date, self.end_date, self.timeframe_str
        )
        # Ensure the DataFrame passed to store_data is the one fetched from the source
        # Need to capture the argument passed to store_data for pd.testing.assert_frame_equal
        args, kwargs = self.mock_cache.store_data.call_args
        self.assertEqual(args[0], expected_key)
        pd.testing.assert_frame_equal(args[1], self.sample_df)
        
        pd.testing.assert_frame_equal(result_df, self.sample_df)

    def test_fetch_historical_data_cache_miss_fetch_empty(self):
        expected_key = self._generate_expected_cache_key(
            self.symbol, self.timeframe_str, self.start_date, self.end_date, self.default_source_type
        )
        self.mock_cache.get_data.return_value = None # Cache miss
        self.mock_factory.get_data_source.return_value = self.mock_data_source
        self.mock_data_source.fetch_data.return_value = self.empty_df.copy() # Source returns empty

        result_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_str, self.start_date, self.end_date
        )
        self.mock_cache.store_data.assert_not_called() # Cache does not store empty DFs by default
        self.assertTrue(result_df.empty)


    def test_fetch_historical_data_factory_fails(self):
        self.mock_cache.get_data.return_value = None # Cache miss
        self.mock_factory.get_data_source.return_value = None # Factory fails

        result_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_str, self.start_date, self.end_date
        )
        self.assertTrue(result_df.empty)
        self.mock_data_source.fetch_data.assert_not_called()
        self.mock_cache.store_data.assert_not_called()

    def test_fetch_historical_data_source_fetch_exception(self):
        self.mock_cache.get_data.return_value = None # Cache miss
        self.mock_factory.get_data_source.return_value = self.mock_data_source
        self.mock_data_source.fetch_data.side_effect = Exception("Data source network error")

        result_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_str, self.start_date, self.end_date
        )
        self.assertTrue(result_df.empty)
        self.mock_cache.store_data.assert_not_called()

    def test_fetch_historical_data_override_source_type_and_kwargs(self):
        custom_source_type = "CUSTOM_CSV"
        custom_source_kwargs = {"csv_directory_path": "/custom/path"}
        expected_key = self._generate_expected_cache_key(
            self.symbol, self.timeframe_str, self.start_date, self.end_date, custom_source_type
        )
        
        self.mock_cache.get_data.return_value = None
        self.mock_factory.get_data_source.return_value = self.mock_data_source
        self.mock_data_source.fetch_data.return_value = self.sample_df.copy()

        self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe_str, self.start_date, self.end_date,
            source_type=custom_source_type, source_kwargs=custom_source_kwargs
        )
        
        self.mock_factory.get_data_source.assert_called_once_with(
            custom_source_type, **custom_source_kwargs
        )
        # Similar to test_fetch_historical_data_cache_miss_fetch_success, check arguments to store_data
        args, kwargs = self.mock_cache.store_data.call_args
        self.assertEqual(args[0], expected_key)
        pd.testing.assert_frame_equal(args[1], self.sample_df)


    # --- Test get_all_data_sorted_by_timestamp() ---
    def test_get_all_data_sorted_success(self):
        sym1 = "SYM1"
        sym2 = "SYM2"
        symbols = [sym1, sym2]

        df_sym1 = pd.DataFrame({
            'timestamp': pd.to_datetime([datetime(2023,1,1,10,0, tzinfo=timezone.utc), datetime(2023,1,2,10,0, tzinfo=timezone.utc)]),
            'open': [10, 11], 'high': [12, 13], 'low': [8, 9], 'close': [11, 12], 'volume': [100, 110]
        })
        df_sym2 = pd.DataFrame({
            'timestamp': pd.to_datetime([datetime(2023,1,1,9,0, tzinfo=timezone.utc), datetime(2023,1,3,10,0, tzinfo=timezone.utc)]),
            'open': [20, 21], 'high': [22, 23], 'low': [18, 19], 'close': [21, 22], 'volume': [200, 210]
        })
        
        def mock_fetch_side_effect(symbol_arg, tf_arg, start_arg, end_arg, source_type=None, source_kwargs=None):
            self.assertEqual(tf_arg, self.timeframe_str)
            self.assertEqual(start_arg, self.start_date) # Assuming these are fixed for this test call
            self.assertEqual(end_arg, self.end_date)     # Same as above
            if symbol_arg == sym1: return df_sym1.copy()
            if symbol_arg == sym2: return df_sym2.copy()
            return self.empty_df.copy()

        with patch.object(self.data_manager, 'fetch_historical_data', side_effect=mock_fetch_side_effect) as mock_fetch:
            all_data = self.data_manager.get_all_data_sorted_by_timestamp(
                symbols, self.timeframe_str, self.start_date, self.end_date
            )
            
            expected_fetch_calls = [
                call(sym1, self.timeframe_str, self.start_date, self.end_date, source_type=None, source_kwargs=None),
                call(sym2, self.timeframe_str, self.start_date, self.end_date, source_type=None, source_kwargs=None)
            ]
            mock_fetch.assert_has_calls(expected_fetch_calls, any_order=True)

            self.assertEqual(len(all_data), 4) 

            # Expected sorted timestamps (naive for comparison simplicity, assuming UTC input)
            ts_s2_early = datetime(2023,1,1,9,0).replace(tzinfo=None) 
            ts_s1_mid1 = datetime(2023,1,1,10,0).replace(tzinfo=None)
            ts_s1_mid2 = datetime(2023,1,2,10,0).replace(tzinfo=None)
            ts_s2_late = datetime(2023,1,3,10,0).replace(tzinfo=None)
            
            self.assertEqual(all_data[0][0].replace(tzinfo=None), ts_s2_early)
            self.assertEqual(all_data[1][0].replace(tzinfo=None), ts_s1_mid1)
            self.assertEqual(all_data[2][0].replace(tzinfo=None), ts_s1_mid2)
            self.assertEqual(all_data[3][0].replace(tzinfo=None), ts_s2_late)

            self.assertEqual(all_data[0][1][sym2].open, 20)
            self.assertEqual(all_data[0][1][sym2].timeframe, self.timeframe_enum)
            self.assertEqual(all_data[1][1][sym1].open, 10)
            self.assertEqual(all_data[1][1][sym1].timeframe, self.timeframe_enum)


    def test_get_all_data_sorted_one_symbol_empty(self):
        sym1 = "SYM1_GOOD"
        sym2 = "SYM2_EMPTY"
        symbols = [sym1, sym2]
        df_sym1 = self.sample_df.copy()

        def mock_fetch_side_effect_one_empty(symbol_arg, tf_arg, start_arg, end_arg, source_type=None, source_kwargs=None):
            if symbol_arg == sym1: return df_sym1.copy()
            if symbol_arg == sym2: return self.empty_df.copy()
            return self.empty_df.copy()

        with patch.object(self.data_manager, 'fetch_historical_data', side_effect=mock_fetch_side_effect_one_empty):
            all_data = self.data_manager.get_all_data_sorted_by_timestamp(
                symbols, self.timeframe_str, self.start_date, self.end_date
            )
            self.assertEqual(len(all_data), len(df_sym1)) 
            if all_data: # Ensure all_data is not empty before indexing
                 self.assertNotIn(sym2, all_data[0][1]) 
                 self.assertIn(sym1, all_data[0][1])


    def test_get_all_data_timeframe_mapping(self):
        minimal_df = pd.DataFrame({
            'timestamp': [datetime(2023,1,1,10,0,tzinfo=timezone.utc)],
            'open': [1], 'high': [1], 'low': [1], 'close': [1], 'volume': [1]
        })
        
        test_timeframes = {
            "1D": Timeframe.DAY_1, "5MIN": Timeframe.MINUTE_5,
            "1MIN": Timeframe.MINUTE_1, "INVALID_TF": None
        }

        with patch.object(self.data_manager, 'fetch_historical_data', return_value=minimal_df.copy()):
            for tf_str, expected_tf_enum in test_timeframes.items():
                with self.subTest(timeframe_str=tf_str):
                    all_data = self.data_manager.get_all_data_sorted_by_timestamp(
                        [self.symbol], tf_str, self.start_date, self.end_date
                    )
                    self.assertTrue(all_data, f"No data returned for timeframe {tf_str}")
                    candle = all_data[0][1][self.symbol]
                    self.assertEqual(candle.timeframe, expected_tf_enum, 
                                     f"Candle timeframe enum mismatch for input string '{tf_str}'")

if __name__ == '__main__':
    unittest.main()

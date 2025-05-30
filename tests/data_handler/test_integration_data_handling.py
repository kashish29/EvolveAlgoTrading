import unittest
import pandas as pd
from datetime import datetime, timezone
import os
import shutil # For cleaning up temp directory
import tempfile # For creating a temporary directory securely

from src.data_handler.historical_data_manager import HistoricalDataManager
from src.data_handler.data_source_factory import DataSourceFactory
from src.data_handler.data_cache import DataCache
from src.core.models import Timeframe # For Candle objects, if checking them

# Sample CSV content for integration tests
SAMPLE_INTEGRATION_CSV_HEADER = "timestamp,open,high,low,close,volume"
SAMPLE_INTEGRATION_CSV_DATA_ROWS = [
    ("2023-01-15T10:00:00Z", 100.0, 102.5, 99.5, 101.0, 10000),
    ("2023-01-15T10:05:00Z", 101.0, 103.0, 100.5, 102.0, 12000), # Included in range
    ("2023-01-15T10:10:00Z", 102.0, 104.5, 101.5, 103.5, 11000), # Included in range
    ("2023-01-16T09:00:00Z", 103.5, 105.0, 103.0, 104.0, 15000), # Outside initial fetch range but in file
]

class TestIntegrationDataHandling(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a temporary directory to store CSV files for testing
        cls.temp_dir = tempfile.mkdtemp(prefix="integration_csv_") # Secure temp dir
        # os.makedirs(cls.temp_dir, exist_ok=True) # mkdtemp already creates it

        # Create a sample CSV file
        cls.symbol = "INTEGRATION_TEST_SYM"
        cls.timeframe = "5MIN" # Corresponds to data rows
        cls.csv_file_path = os.path.join(cls.temp_dir, f"{cls.symbol}_{cls.timeframe}.csv")

        # Prepare CSV data string
        csv_content_list = [SAMPLE_INTEGRATION_CSV_HEADER]
        for row in SAMPLE_INTEGRATION_CSV_DATA_ROWS:
            csv_content_list.append(",".join(map(str, row)))
        
        cls.full_csv_content = "\n".join(csv_content_list)

        with open(cls.csv_file_path, 'w') as f:
            f.write(cls.full_csv_content)
            
        print(f"Integration test CSV created at: {cls.csv_file_path}")

    @classmethod
    def tearDownClass(cls):
        # Remove the temporary directory and its contents
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
            print(f"Cleaned up temporary directory: {cls.temp_dir}")

    def setUp(self):
        # Each test gets its own factory and cache to ensure isolation
        self.factory = DataSourceFactory()
        # Using a small cache size to easily test eviction if needed, though not primary focus here
        self.cache = DataCache(max_size=5) 
        
        self.data_manager = HistoricalDataManager(
            data_source_factory=self.factory,
            data_cache=self.cache,
            default_source_type="CSV",
            default_source_kwargs={'csv_directory_path': self.temp_dir}
        )

        # Define dates for fetching data
        self.start_date = datetime(2023, 1, 15, 10, 5, 0, tzinfo=timezone.utc) # Includes 2nd row
        self.end_date = datetime(2023, 1, 15, 10, 10, 0, tzinfo=timezone.utc)   # Includes 3rd row
        
        # Expected data for the date range (2nd and 3rd rows)
        self.expected_df_subset = pd.DataFrame(
            [SAMPLE_INTEGRATION_CSV_DATA_ROWS[1], SAMPLE_INTEGRATION_CSV_DATA_ROWS[2]],
            columns=SAMPLE_INTEGRATION_CSV_HEADER.split(',')
        )
        # Convert columns to appropriate types for comparison
        self.expected_df_subset['timestamp'] = pd.to_datetime(self.expected_df_subset['timestamp'])
        for col in ['open', 'high', 'low', 'close']:
            self.expected_df_subset[col] = pd.to_numeric(self.expected_df_subset[col])
        # Pandas default for integer columns from CSV when some values might be missing is float.
        # If no NaNs, it might be int64. For consistency with potential NaNs from coerce,
        # using float for volume or careful Int64 if pandas version supports it well.
        # Given our data source standardizes volume to numeric (float or int if possible),
        # direct comparison after to_numeric should be fine.
        self.expected_df_subset['volume'] = pd.to_numeric(self.expected_df_subset['volume'])


    def test_fetch_data_cache_miss_then_hit(self):
        # 1. First fetch (cache miss)
        print("\nIntegration Test: First fetch (cache miss)...")
        fetched_df_miss = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe, self.start_date, self.end_date
        )
        
        self.assertFalse(fetched_df_miss.empty, "DataFrame should not be empty on first fetch.")
        self.assertEqual(len(fetched_df_miss), 2, "Should fetch 2 records based on date range.")
        pd.testing.assert_frame_equal(fetched_df_miss.reset_index(drop=True), 
                                      self.expected_df_subset.reset_index(drop=True),
                                      check_dtype=False) 

        # Verify data is in cache (key generation needs to be consistent with HDM)
        cache_key = self.data_manager._generate_cache_key(
            self.symbol, self.timeframe, self.start_date, self.end_date, "CSV"
        )
        self.assertIn(cache_key, self.cache, "Data should be in cache after first fetch.")

        # 2. Second fetch (cache hit)
        print("Integration Test: Second fetch (cache hit)...")
        
        fetched_df_hit = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe, self.start_date, self.end_date
        )
        
        self.assertFalse(fetched_df_hit.empty, "DataFrame should not be empty on cache hit.")
        pd.testing.assert_frame_equal(fetched_df_hit.reset_index(drop=True), 
                                      self.expected_df_subset.reset_index(drop=True),
                                      check_dtype=False)
        
    def test_data_integrity_and_column_types(self):
        print("\nIntegration Test: Data integrity and column types...")
        fetched_df = self.data_manager.fetch_historical_data(
            self.symbol, self.timeframe, self.start_date, self.end_date
        )
        
        self.assertFalse(fetched_df.empty)
        
        # Check column names
        expected_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        self.assertListEqual(list(fetched_df.columns), expected_columns)
        
        # Check dtypes (as standardized by AbstractDataSource/CSVDataSource)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(fetched_df['timestamp']))
        self.assertTrue(pd.api.types.is_numeric_dtype(fetched_df['open']))
        self.assertTrue(pd.api.types.is_numeric_dtype(fetched_df['high']))
        self.assertTrue(pd.api.types.is_numeric_dtype(fetched_df['low']))
        self.assertTrue(pd.api.types.is_numeric_dtype(fetched_df['close']))
        self.assertTrue(pd.api.types.is_numeric_dtype(fetched_df['volume'])) 

        # Check a specific value
        self.assertEqual(fetched_df['open'].iloc[0], 101.0)
        # Timestamps from CSVDataSource are localized to UTC if 'Z' is present, then converted.
        # If input has 'Z', pd.to_datetime makes it tz-aware (UTC).
        # self.start_date and self.end_date are UTC aware.
        # The comparison should be fine.
        self.assertEqual(fetched_df['timestamp'].iloc[0], pd.Timestamp(SAMPLE_INTEGRATION_CSV_DATA_ROWS[1][0]))


    def test_get_all_data_sorted_integration(self):
        print("\nIntegration Test: get_all_data_sorted_by_timestamp...")
        
        all_file_start_date = datetime(2023, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        all_file_end_date = datetime(2023, 1, 16, 23, 59, 59, tzinfo=timezone.utc)
        
        result_list = self.data_manager.get_all_data_sorted_by_timestamp(
            symbols=[self.symbol], 
            timeframe=self.timeframe,
            start_date=all_file_start_date,
            end_date=all_file_end_date
        )
        
        self.assertEqual(len(result_list), 4, "Should retrieve 4 unique timestamp entries from the CSV.")
        
        for i in range(len(result_list) - 1):
            self.assertLess(result_list[i][0], result_list[i+1][0])
            
        first_entry_ts_expected = pd.Timestamp(SAMPLE_INTEGRATION_CSV_DATA_ROWS[0][0]).to_pydatetime()
        # Ensure comparison is between offset-aware and offset-aware or both naive
        # result_list[0][0] should be offset-aware (UTC) as per standardize_data
        self.assertEqual(result_list[0][0], first_entry_ts_expected)
        
        candle_data_first_entry = result_list[0][1].get(self.symbol)
        self.assertIsNotNone(candle_data_first_entry)
        self.assertEqual(candle_data_first_entry.open, SAMPLE_INTEGRATION_CSV_DATA_ROWS[0][1])
        self.assertEqual(candle_data_first_entry.timeframe, Timeframe(self.timeframe))


if __name__ == '__main__':
    unittest.main()

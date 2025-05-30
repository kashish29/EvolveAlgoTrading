import unittest
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
from datetime import datetime
import os

from src.data_handler.csv_data_source import CSVDataSource
from src.data_handler.abstract_data_source import AbstractDataSource # For isinstance check

# Define a sample CSV content string for mocking read_csv
SAMPLE_CSV_DATA = """timestamp,open,high,low,close,volume
2023-01-01T10:00:00Z,100,105,99,102,1000
2023-01-01T10:05:00Z,102,106,101,103,1200
2023-01-02T11:00:00Z,103,107,102,105,1500
2023-01-03T12:00:00Z,105,109,104,108,1800
"""

EMPTY_CSV_DATA = "timestamp,open,high,low,close,volume\n" # Header only

MALFORMED_CSV_DATA = "timestamp,open,high,low,close,volume\nrandom_text\n1,2,3,4,5,6"


class TestCSVDataSource(unittest.TestCase):

    def setUp(self):
        self.test_csv_dir = "test_temp_csv_data" # A temporary directory for testing path construction
        # We won't actually create this dir, as os.path.isdir and os.path.exists will be mocked.
        
        # Mock os.path.isdir to always return True for the constructor check
        # This patch is for the CSVDataSource constructor specifically.
        self.isdir_patcher = patch('src.data_handler.csv_data_source.os.path.isdir', return_value=True)
        self.mock_isdir = self.isdir_patcher.start()
        
        self.csv_source = CSVDataSource(csv_directory_path=self.test_csv_dir)
        
        # Pre-parse CSV data to DataFrames to be used by mocks
        # This uses the real pd.read_csv before any method-level patches are active
        try:
            from io import StringIO
            self.SAMPLE_DF = pd.read_csv(StringIO(SAMPLE_CSV_DATA))
            self.EMPTY_DF_WITH_COLUMNS = pd.read_csv(StringIO(EMPTY_CSV_DATA))
            self.MALFORMED_DF_MISSING_COL = pd.read_csv(StringIO(
                "timestamp,open,high,low,close\n2023-01-01T10:00:00Z,100,105,99,102"
            ))
            self.BAD_OHLC_DF = pd.read_csv(StringIO(
                "timestamp,open,high,low,close,volume\n2023-01-01T10:00:00Z,一百,105,99,102,1000"
            ))
        except ImportError: # Fallback for pandas < 2.0
            from pandas.io.common import StringIO
            self.SAMPLE_DF = pd.read_csv(StringIO(SAMPLE_CSV_DATA))
            self.EMPTY_DF_WITH_COLUMNS = pd.read_csv(StringIO(EMPTY_CSV_DATA))
            self.MALFORMED_DF_MISSING_COL = pd.read_csv(StringIO(
                "timestamp,open,high,low,close\n2023-01-01T10:00:00Z,100,105,99,102"
            ))
            self.BAD_OHLC_DF = pd.read_csv(StringIO(
                "timestamp,open,high,low,close,volume\n2023-01-01T10:00:00Z,一百,105,99,102,1000"
            ))

    def tearDown(self):
        self.isdir_patcher.stop() # Stop the patcher

    def test_csv_data_source_instantiation(self):
        self.assertIsInstance(self.csv_source, AbstractDataSource)
        self.assertEqual(self.csv_source.csv_directory_path, self.test_csv_dir)

    def test_construct_file_path(self):
        symbol = "TEST/SYM"
        timeframe = "1H"
        expected_filename = "TEST_SYM_1H.csv" # Symbol sanitized
        expected_path = os.path.join(self.test_csv_dir, expected_filename)
        self.assertEqual(self.csv_source._construct_file_path(symbol, timeframe), expected_path)

    @patch('src.data_handler.csv_data_source.os.path.exists')
    @patch('src.data_handler.csv_data_source.pd.read_csv')
    def test_fetch_data_success_and_filtering(self, mock_read_csv, mock_exists):
        mock_exists.return_value = True # Assume file exists
        mock_read_csv.return_value = self.SAMPLE_DF.copy()

        start_date = datetime(2023, 1, 1, 10, 5, 0) # Inclusive, should get 2nd record onwards
        end_date = datetime(2023, 1, 2, 11, 0, 0)   # Inclusive, should get up to 3rd record
        symbol = "ANY_SYMBOL"
        timeframe = "5MIN" # Timeframe used for filename construction

        result_df = self.csv_source.fetch_data(symbol, start_date, end_date, timeframe)

        # Check file path construction and existence check
        expected_file_path = os.path.join(self.test_csv_dir, f"{symbol}_{timeframe}.csv")
        mock_exists.assert_called_once_with(expected_file_path)
        mock_read_csv.assert_called_once_with(expected_file_path)

        self.assertFalse(result_df.empty)
        self.assertEqual(len(result_df), 2) # 2023-01-01T10:05:00Z and 2023-01-02T11:00:00Z
        
        # Verify timestamps (they should be datetime objects after standardization)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result_df['timestamp']))
        self.assertEqual(result_df['timestamp'].iloc[0], pd.Timestamp("2023-01-01T10:05:00Z"))
        self.assertEqual(result_df['timestamp'].iloc[1], pd.Timestamp("2023-01-02T11:00:00Z"))
        self.assertEqual(result_df['open'].iloc[0], 102)

    @patch('os.path.exists', return_value=False) # File does not exist
    def test_fetch_data_file_not_found(self, mock_exists):
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        result_df = self.csv_source.fetch_data(symbol="TEST", start_date=start_date, end_date=end_date, timeframe="1D")
        
        self.assertTrue(result_df.empty)
        # mock_exists should have been called
        mock_exists.assert_called()


    @patch('src.data_handler.csv_data_source.os.path.exists', return_value=True)
    @patch('src.data_handler.csv_data_source.pd.read_csv')
    def test_fetch_data_empty_csv(self, mock_read_csv, mock_exists):
        mock_read_csv.return_value = self.EMPTY_DF_WITH_COLUMNS.copy()
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        result_df = self.csv_source.fetch_data(symbol="TEST", start_date=start_date, end_date=end_date, timeframe="1D")
        
        self.assertTrue(result_df.empty)

    @patch('src.data_handler.csv_data_source.os.path.exists', return_value=True)
    @patch('src.data_handler.csv_data_source.pd.read_csv', side_effect=pd.errors.EmptyDataError) # Simulate pandas error for malformed/empty file
    def test_fetch_data_pandas_empty_data_error(self, mock_read_csv, mock_exists):
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        result_df = self.csv_source.fetch_data(symbol="TEST", start_date=start_date, end_date=end_date, timeframe="1D")
        self.assertTrue(result_df.empty)

    @patch('src.data_handler.csv_data_source.os.path.exists', return_value=True)
    @patch('src.data_handler.csv_data_source.pd.read_csv')
    def test_fetch_data_missing_required_columns(self, mock_read_csv, mock_exists):
        mock_read_csv.return_value = self.MALFORMED_DF_MISSING_COL.copy()
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        result_df = self.csv_source.fetch_data(symbol="TEST", start_date=start_date, end_date=end_date, timeframe="1D")
        
        # Validation should fail, returning an empty DataFrame
        self.assertTrue(result_df.empty)

    @patch('src.data_handler.csv_data_source.os.path.exists', return_value=True)
    @patch('src.data_handler.csv_data_source.pd.read_csv')
    def test_fetch_data_standardization_failure_non_numeric_ohlc(self, mock_read_csv, mock_exists):
        mock_read_csv.return_value = self.BAD_OHLC_DF.copy()
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        # Corrected argument order
        result_df = self.csv_source.fetch_data(symbol="TEST", start_date=start_date, end_date=end_date, timeframe="1D")
        
        self.assertFalse(result_df.empty, "DataFrame should not be empty even with NaN values if columns exist.")
        self.assertTrue(result_df['open'].isna().all(), "Open column should be NaN after failed conversion.")


    @patch('src.data_handler.csv_data_source.os.path.exists', return_value=True)
    @patch('src.data_handler.csv_data_source.pd.read_csv')
    def test_fetch_data_no_data_in_date_range(self, mock_read_csv, mock_exists):
        mock_read_csv.return_value = self.SAMPLE_DF.copy()

        # Date range that doesn't overlap with any data in SAMPLE_CSV_DATA
        start_date = datetime(2024, 1, 1) 
        end_date = datetime(2024, 1, 2)
        
        result_df = self.csv_source.fetch_data(symbol="TEST", start_date=start_date, end_date=end_date, timeframe="1D")
        self.assertTrue(result_df.empty)


    def test_csv_data_source_constructor_dir_not_found(self):
        # Test constructor when directory does not exist
        # This needs to patch os.path.isdir where CSVDataSource looks for it.
        with patch('src.data_handler.csv_data_source.os.path.isdir', return_value=False) as mock_is_dir_constructor_check:
            with self.assertRaises(ValueError) as context:
                CSVDataSource(csv_directory_path="non_existent_dir")
            self.assertIn("CSV directory not found", str(context.exception))
            mock_is_dir_constructor_check.assert_called_once_with("non_existent_dir")


if __name__ == '__main__':
    unittest.main()

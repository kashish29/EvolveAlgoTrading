import pandas as pd
from datetime import datetime
import os
from typing import Optional

from .abstract_data_source import AbstractDataSource

class CSVDataSource(AbstractDataSource):
    """
    Data source implementation for fetching data from CSV files.
    Assumes CSV files are stored in a directory specified during initialization.
    Filename convention: {symbol}_{timeframe}.csv (e.g., "SBIN-EQ_1D.csv")
    """

    def __init__(self, csv_directory_path: str):
        """
        Initializes the CSVDataSource.

        Args:
            csv_directory_path (str): The path to the directory containing CSV files.
                                      This path should be absolute or relative to the project root.
        """
        if not os.path.isdir(csv_directory_path):
            # Consider creating the directory if it doesn't exist, or raising a more specific error.
            # For now, let's assume it should exist.
            raise ValueError(f"CSV directory not found or is not a directory: {csv_directory_path}")
        self.csv_directory_path = csv_directory_path
        print(f"CSVDataSource initialized with directory: {self.csv_directory_path}")

    def _construct_file_path(self, symbol: str, timeframe: str) -> str:
        """Helper to construct the full path for a CSV file."""
        # Sanitize symbol and timeframe to be safe for filenames if necessary
        filename = f"{symbol.replace('/', '_')}_{timeframe}.csv" # Basic sanitization for symbol
        return os.path.join(self.csv_directory_path, filename)

    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime, timeframe: str) -> pd.DataFrame:
        """
        Fetches historical market data from a CSV file.

        The CSV file is expected to have 'timestamp', 'open', 'high', 'low', 'close', 
        and 'volume' columns. The 'timestamp' column should be parsable into datetime objects.

        Data within the CSV is filtered by the provided start_date and end_date.

        Args:
            symbol (str): The trading symbol.
            start_date (datetime): The start date for filtering the data (inclusive).
            end_date (datetime): The end date for filtering the data (inclusive).
            timeframe (str): The timeframe for the data (used to determine filename).

        Returns:
            pd.DataFrame: A Pandas DataFrame with filtered, standardized, and validated data.
                          Returns an empty DataFrame if the file is not found, data is invalid,
                          or no data matches the date range.
        """
        file_path = self._construct_file_path(symbol, timeframe)
        print(f"CSVDataSource: Attempting to load data from {file_path}")

        if not os.path.exists(file_path):
            print(f"CSVDataSource: File not found: {file_path}. Returning empty DataFrame.")
            return pd.DataFrame() # Return empty DataFrame if file doesn't exist

        try:
            df = pd.read_csv(file_path)
            
            if df.empty:
                print(f"CSVDataSource: File {file_path} is empty. Returning empty DataFrame.")
                return pd.DataFrame()

            # Standardize data (e.g., convert 'timestamp' to datetime, numeric types for OHLCV)
            # This also handles the case where 'timestamp' might be missing or not convertible.
            df_standardized = self.standardize_data(df)

            if df_standardized.empty and not df.empty: # Standardization failed critically
                print(f"CSVDataSource: Data standardization failed for {file_path}. Check data formats.")
                return pd.DataFrame()
            
            # Validate data structure (e.g., required columns are present)
            if not self.validate_data(df_standardized):
                print(f"CSVDataSource: Data validation failed for {file_path} after standardization.")
                return pd.DataFrame() # Return empty if validation fails

            # Filter by date range - ensure 'timestamp' is datetime for comparison
            if 'timestamp' in df_standardized.columns and pd.api.types.is_datetime64_any_dtype(df_standardized['timestamp']):
                # Ensure start_date and end_date are timezone-naive if df_standardized['timestamp'] is naive,
                # or localize them if df_standardized['timestamp'] is timezone-aware.
                # Assuming naive datetime objects for comparison for simplicity here.
                # If timestamps in CSV can have timezone, this needs more robust handling.
                
                # Convert start_date and end_date to pandas Timestamp for comparison if they are Python datetimes
                pd_start_date = pd.Timestamp(start_date)
                pd_end_date = pd.Timestamp(end_date)

                # Check if timestamps in DataFrame are timezone-aware
                if df_standardized['timestamp'].dt.tz is not None:
                    # If so, make sure start_date and end_date are also timezone-aware (or convert df to naive)
                    # For simplicity, let's assume CSV timestamps are naive or UTC. If they are aware,
                    # start_date and end_date should be made aware to the same timezone.
                    # This example assumes naive comparison or that timezones are already aligned.
                     pd_start_date = pd_start_date.tz_localize(df_standardized['timestamp'].dt.tz) if pd_start_date.tzinfo is None else pd_start_date.tz_convert(df_standardized['timestamp'].dt.tz)
                     pd_end_date = pd_end_date.tz_localize(df_standardized['timestamp'].dt.tz) if pd_end_date.tzinfo is None else pd_end_date.tz_convert(df_standardized['timestamp'].dt.tz)


                mask = (df_standardized['timestamp'] >= pd_start_date) & \
                       (df_standardized['timestamp'] <= pd_end_date)
                df_filtered = df_standardized.loc[mask]
            else:
                print("CSVDataSource: 'timestamp' column not suitable for date filtering. Returning all data.")
                # If timestamp column is not suitable (e.g., missing, not datetime after standardization),
                # we might return the whole df or an empty one.
                # For now, let's return the unfiltered (but standardized and validated) df,
                # or an empty one if timestamp is critical for the use case.
                # Given the spec, data should have a valid timestamp. If not, it's problematic.
                # Let's assume if validate_data passed, and standardize_data tried, timestamp is there.
                # If filtering cannot be done, it might be an issue.
                # For now, let's return empty if timestamp is not in expected state for filtering.
                if not ('timestamp' in df_standardized.columns and pd.api.types.is_datetime64_any_dtype(df_standardized['timestamp'])):
                    print("CSVDataSource: Critical 'timestamp' issue. Returning empty DataFrame.")
                    return pd.DataFrame()
                df_filtered = df_standardized # Fallback, though ideally this path means bad data.


            if df_filtered.empty:
                print(f"CSVDataSource: No data found in {file_path} for the period {start_date} to {end_date}.")
            
            # Final check on required columns after filtering, though validate_data should ensure this.
            # Required columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            # df_filtered should already conform from validate_data.

            print(f"CSVDataSource: Successfully fetched {len(df_filtered)} records from {file_path} for the specified range.")
            return df_filtered.reset_index(drop=True) # Reset index after filtering

        except pd.errors.EmptyDataError:
            print(f"CSVDataSource: File {file_path} is empty or malformed (EmptyDataError). Returning empty DataFrame.")
            return pd.DataFrame()
        except Exception as e:
            print(f"CSVDataSource: An error occurred while reading or processing {file_path}: {e}")
            return pd.DataFrame() # Return empty DataFrame on other errors

    def __repr__(self) -> str:
        return f"<CSVDataSource(directory='{self.csv_directory_path}')>"

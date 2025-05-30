import pandas as pd
from datetime import datetime
from typing import Optional, Any, Dict, List, Tuple # Corrected List and Tuple import
from collections import defaultdict

from src.core.models import Candle, Timeframe
from .data_source_factory import DataSourceFactory
from .data_cache import DataCache
from .abstract_data_source import AbstractDataSource # Ensure this is imported


class HistoricalDataManager:
    def __init__(self, 
                 data_source_factory: DataSourceFactory, 
                 data_cache: DataCache,
                 default_source_type: str = "CSV",
                 default_source_kwargs: Optional[Dict[str, Any]] = None):
        """
        Initializes the HistoricalDataManager with a data source factory and a cache.

        Args:
            data_source_factory (DataSourceFactory): Factory to create data source instances.
            data_cache (DataCache): Cache to store and retrieve fetched data.
            default_source_type (str): The default type of data source to use (e.g., "CSV").
            default_source_kwargs (Optional[Dict[str, Any]]): Default keyword arguments 
                                                              for the data source. 
                                                              (e.g., {'csv_directory_path': '/path/to/csvs'})
        """
        if data_source_factory is None:
            raise ValueError("DataSourceFactory cannot be None.")
        if data_cache is None:
            raise ValueError("DataCache cannot be None.")
            
        self.data_source_factory = data_source_factory
        self.data_cache = data_cache
        self.default_source_type = default_source_type
        self.default_source_kwargs = default_source_kwargs if default_source_kwargs is not None else {}
        
        print(f"HistoricalDataManager initialized with default source type: {self.default_source_type}")

    def _generate_cache_key(self, symbol: str, timeframe: str, 
                            start_date: datetime, end_date: datetime, source_type: str) -> str:
        """
        Generates a unique cache key for a data request.
        Includes source_type in the key to differentiate if data could come from multiple sources.
        """
        # Standardize date format for key consistency
        start_date_str = start_date.strftime("%Y%m%d%H%M%S")
        end_date_str = end_date.strftime("%Y%m%d%H%M%S")
        return f"{source_type.upper()}_{symbol}_{timeframe}_{start_date_str}_{end_date_str}"

    def fetch_historical_data(self, 
                              symbol: str, 
                              timeframe: str, # Should be string like "1D", "5MIN"
                              start_date: datetime, 
                              end_date: datetime,
                              source_type: Optional[str] = None,
                              source_kwargs: Optional[Dict[str, Any]] = None
                             ) -> pd.DataFrame: # Return DataFrame, not Optional[DataFrame]
        """
        Fetches historical market data.
        It first checks the cache. If data is not found in cache,
        it uses the DataSourceFactory to get a data source, fetches data,
        stores it in the cache, and then returns it.

        Args:
            symbol (str): The trading symbol (e.g., "SBIN-EQ").
            timeframe (str): The timeframe for the data (e.g., "1D", "5MIN").
            start_date (datetime): The start date for the data.
            end_date (datetime): The end date for the data.
            source_type (Optional[str]): Specific data source type to use. 
                                         If None, uses default_source_type.
            source_kwargs (Optional[Dict[str, Any]]): Arguments for the data source.
                                                      If None, uses default_source_kwargs.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the historical data.
                          The DataFrame will have 'timestamp' (datetime64) and OHLCV columns.
                          Returns an empty DataFrame if data fetching fails or no data is found.
        """
        current_source_type = source_type if source_type is not None else self.default_source_type
        current_source_kwargs = source_kwargs if source_kwargs is not None else self.default_source_kwargs
        
        cache_key = self._generate_cache_key(symbol, timeframe, start_date, end_date, current_source_type)
        
        # 1. Check cache
        cached_df = self.data_cache.get_data(cache_key)
        if cached_df is not None:
            print(f"HistoricalDataManager: Returning cached data for {symbol} ({timeframe})")
            return cached_df

        print(f"HistoricalDataManager: No cache found for {symbol} ({timeframe}). Fetching from source.")

        # 2. If cache miss, get data source from factory
        data_source: Optional[AbstractDataSource] = self.data_source_factory.get_data_source(
            current_source_type, **current_source_kwargs
        )

        if data_source is None:
            print(f"HistoricalDataManager: Failed to get data source for type '{current_source_type}'.")
            return pd.DataFrame() # Return empty DataFrame

        # 3. Fetch data using the data source
        try:
            # The timeframe argument for data_source.fetch_data should be a string
            # If Timeframe enum is passed here, it should be converted to its string value.
            # Assuming 'timeframe' arg to this method is already a string.
            fetched_df = data_source.fetch_data(symbol, start_date, end_date, timeframe)
            
            # fetch_data in AbstractDataSource and its implementations is expected to return
            # an empty DataFrame if there's an error or no data, and it should have already
            # called standardize_data and validate_data.

            if fetched_df is None: # Should ideally not happen if sources return empty DF on failure
                 print(f"HistoricalDataManager: Data source returned None for {symbol}. Returning empty DataFrame.")
                 fetched_df = pd.DataFrame()
            
        except Exception as e:
            print(f"HistoricalDataManager: Error fetching data for {symbol} via {current_source_type}: {e}")
            return pd.DataFrame() # Return empty DataFrame on error

        # 4. Store in cache if data is not empty
        # DataCache.store_data already checks if df is empty and won't store if it is.
        if not fetched_df.empty:
            self.data_cache.store_data(cache_key, fetched_df)
            print(f"HistoricalDataManager: Successfully fetched and cached data for {symbol} ({timeframe}).")
        else:
            print(f"HistoricalDataManager: Fetched empty data for {symbol} ({timeframe}). Not caching.")
            
        # Ensure returned DataFrame has 'timestamp' and ohlcv columns, even if empty.
        # The data_source itself should guarantee this based on AbstractDataSource contract.
        # If fetched_df is empty, it should ideally have these columns defined.
        # If not, we might need to enforce it here.
        # For now, rely on data_source.standardize_data() to have handled this.

        return fetched_df


    def get_all_data_sorted_by_timestamp(self, 
                                         symbols: List[str], # Use List from typing
                                         timeframe: str, # Expect string like "1D", "5MIN"
                                         start_date: datetime, 
                                         end_date: datetime,
                                         source_type: Optional[str] = None,
                                         source_kwargs: Optional[Dict[str, Any]] = None
                                        ) -> List[Tuple[datetime, Dict[str, Candle]]]: # Use List, Tuple, Dict
        """
        Fetches historical data for multiple symbols using the new fetch_historical_data method,
        combines them, and sorts by timestamp.

        Args:
            symbols (List[str]): A list of trading symbols.
            timeframe (str): The timeframe for the data (e.g., "1D", "5MIN").
            start_date (datetime): The start date for the data.
            end_date (datetime): The end date for the data.
            source_type (Optional[str]): Specific data source type to use.
            source_kwargs (Optional[Dict[str, Any]]): Arguments for the data source.

        Returns:
            List[Tuple[datetime, Dict[str, Candle]]]: Sorted list of (timestamp, {symbol: Candle}).
        """
        all_candles_by_timestamp: defaultdict[datetime, Dict[str, Candle]] = defaultdict(dict)
        
        timeframe_enum_val: Optional[Timeframe] = None
        try:
            # Attempt to map the string timeframe to the Timeframe enum
            # This is for creating Candle objects. The fetch_historical_data method
            # will pass the timeframe string directly to the data source.
            timeframe_enum_val = Timeframe(timeframe) # Direct mapping if string matches enum member name
        except ValueError:
            # Fallback for common patterns like "1D" to Timeframe.DAY_1
            # This mapping logic should be robust or centralized if many variations are expected.
            tf_upper = timeframe.upper()
            if tf_upper == "1D": timeframe_enum_val = Timeframe.DAY_1
            elif tf_upper == "5MIN": timeframe_enum_val = Timeframe.MINUTE_5
            elif tf_upper == "1MIN": timeframe_enum_val = Timeframe.MINUTE_1
            # Add more mappings as necessary
            else:
                try:
                    # Try direct match after basic processing (e.g. "MINUTE_5" for Timeframe.MINUTE_5)
                    timeframe_enum_val = Timeframe[tf_upper]
                except KeyError:
                    print(f"HistoricalDataManager Warning: Could not map timeframe string '{timeframe}' to Timeframe enum for Candle creation. Candle.timeframe might be None.")
                    # timeframe_enum_val remains None

        for symbol in symbols:
            print(f"HistoricalDataManager (get_all_data): Fetching data for symbol: {symbol}, timeframe: {timeframe}")
            df = self.fetch_historical_data(
                symbol, timeframe, start_date, end_date, 
                source_type=source_type, source_kwargs=source_kwargs
            )

            if df is not None and not df.empty:
                # Ensure 'timestamp' is datetime after fetching
                if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                    print(f"HistoricalDataManager Warning: Timestamp column for {symbol} is not datetime. Attempting conversion.")
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    df.dropna(subset=['timestamp'], inplace=True) # Drop rows where timestamp conversion failed

                for _, row in df.iterrows():
                    ts = row['timestamp'] # Already a datetime object from standardize_data
                    
                    # Ensure ts is a Python datetime object, not just pandas.Timestamp for defaultdict key
                    if isinstance(ts, pd.Timestamp):
                        ts = ts.to_pydatetime()

                    candle = Candle(
                        timestamp=ts,
                        symbol=symbol,
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=int(row['volume']) if 'volume' in row and pd.notna(row['volume']) else 0,
                        timeframe=timeframe_enum_val # Use the mapped Timeframe enum
                    )
                    all_candles_by_timestamp[ts][symbol] = candle
            else:
                print(f"HistoricalDataManager (get_all_data): No data fetched for symbol: {symbol}")

        sorted_timestamps = sorted(all_candles_by_timestamp.keys())
        result = [(ts, all_candles_by_timestamp[ts]) for ts in sorted_timestamps]
        
        print(f"HistoricalDataManager (get_all_data): Processed and sorted data for {len(symbols)} symbols. Returning {len(result)} timestamp entries.")
        return result

# Example Usage (to be updated for new constructor and methods)
if __name__ == '__main__':
    from .csv_data_source import CSVDataSource # For example
    import os
    
    # Setup: Create a dummy CSV file for the example
    # This setup would typically be part of a test suite or example script.
    
    # Create a temporary directory for CSV data if it doesn't exist
    temp_csv_dir = "temp_csv_data_for_hdm_example"
    os.makedirs(temp_csv_dir, exist_ok=True)
    
    # Create a dummy CSV file: INFY-EQ_1D.csv
    dummy_symbol = "INFY-EQ"
    dummy_timeframe = "1D"
    dummy_file_path = os.path.join(temp_csv_dir, f"{dummy_symbol}_{dummy_timeframe}.csv")
    
    # Sample data for the CSV
    sample_dates = pd.to_datetime([datetime(2023, 1, 15), datetime(2023, 1, 16), datetime(2023, 1, 17)])
    sample_data_dict = {
        'timestamp': sample_dates,
        'open': [300, 305, 310],
        'high': [310, 315, 320],
        'low': [290, 295, 300],
        'close': [305, 310, 315],
        'volume': [10000, 11000, 12000]
    }
    dummy_df = pd.DataFrame(sample_data_dict)
    dummy_df.to_csv(dummy_file_path, index=False)
    print(f"Example Usage: Created dummy CSV file at {dummy_file_path}")

    # 1. Initialize components
    factory = DataSourceFactory()
    cache = DataCache(max_size=10) # Example cache with max size
    
    # Provide necessary kwargs for the default CSV source
    hdm_source_kwargs = {'csv_directory_path': temp_csv_dir}
    
    data_manager = HistoricalDataManager(
        data_source_factory=factory, 
        data_cache=cache,
        default_source_type="CSV", # Explicitly set, though it's the default in constructor
        default_source_kwargs=hdm_source_kwargs
    )

    # 2. Parameters for data fetching
    symbol_to_fetch = dummy_symbol # "INFY-EQ"
    timeframe_to_fetch = dummy_timeframe # "1D"
    start_dt = datetime(2023, 1, 15) # Inclusive
    end_dt = datetime(2023, 1, 16)   # Inclusive
    
    # 3. Fetch single historical data
    print(f"\nExample Usage: Fetching single historical data for {symbol_to_fetch}...")
    historical_data_df = data_manager.fetch_historical_data(
        symbol_to_fetch, timeframe_to_fetch, start_dt, end_dt
    )

    if historical_data_df is not None and not historical_data_df.empty:
        print(f"\nSuccessfully fetched data for {symbol_to_fetch} via new HDM:")
        print(historical_data_df)
    else:
        print(f"\nFailed to fetch data or no data found for {symbol_to_fetch} via new HDM.")

    # 4. Fetch again (should hit cache)
    print(f"\nExample Usage: Fetching same data again for {symbol_to_fetch} (should hit cache)...")
    historical_data_df_cached = data_manager.fetch_historical_data(
        symbol_to_fetch, timeframe_to_fetch, start_dt, end_dt
    )
    if historical_data_df_cached is not None:
        print("Cached version:")
        print(historical_data_df_cached)
        
    # 5. Fetch data for multiple symbols (get_all_data_sorted_by_timestamp)
    # Create another dummy CSV for a second symbol
    dummy_symbol_2 = "REL-EQ"
    dummy_file_path_2 = os.path.join(temp_csv_dir, f"{dummy_symbol_2}_{dummy_timeframe}.csv")
    sample_dates_2 = pd.to_datetime([datetime(2023, 1, 15), datetime(2023, 1, 16)])
    sample_data_dict_2 = {
        'timestamp': sample_dates_2,
        'open': [2500, 2510], 'high': [2520, 2530], 'low': [2480, 2490],
        'close': [2510, 2520], 'volume': [50000, 55000]
    }
    dummy_df_2 = pd.DataFrame(sample_data_dict_2)
    dummy_df_2.to_csv(dummy_file_path_2, index=False)
    print(f"Example Usage: Created dummy CSV file at {dummy_file_path_2}")
    
    print(f"\nExample Usage: Fetching all data sorted for symbols [{symbol_to_fetch}, {dummy_symbol_2}]...")
    all_sorted_data = data_manager.get_all_data_sorted_by_timestamp(
        symbols=[symbol_to_fetch, dummy_symbol_2],
        timeframe=timeframe_to_fetch,
        start_date=datetime(2023, 1, 1,0,0,0), # Wider range to get all data from files
        end_date=datetime(2023, 1, 30,0,0,0)
    )

    if all_sorted_data:
        print("\nSuccessfully fetched and sorted data for multiple symbols:")
        for ts, candle_dict in all_sorted_data:
            print(f"Timestamp: {ts}")
            for sym, candle_obj in candle_dict.items():
                print(f"  {sym}: O={candle_obj.open}, H={candle_obj.high}, L={candle_obj.low}, C={candle_obj.close}, V={candle_obj.volume}, TF={candle_obj.timeframe}")
    else:
        print("\nFailed to fetch or no data found for multiple symbols.")
        
    # Clean up dummy CSV files and directory
    try:
        os.remove(dummy_file_path)
        os.remove(dummy_file_path_2)
        os.rmdir(temp_csv_dir)
        print("\nExample Usage: Cleaned up dummy CSV files and directory.")
    except OSError as e:
        print(f"\nExample Usage: Error cleaning up dummy files: {e}")

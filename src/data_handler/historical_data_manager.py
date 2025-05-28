import pandas as pd
from datetime import datetime
from typing import Optional, Any
from collections import defaultdict # Added import
from src.core.models import Candle, Timeframe  # Added import
# Attempt to import the mock client, handling potential import errors gracefully for standalone use/testing.
try:
    from src.broker_api.fyers_client import MockFyersClient
except ImportError:
    print("Warning: MockFyersClient not found at its expected location. Ensure PYTHONPATH is set correctly or full framework is used.")
    MockFyersClient = None # Define it as None if import fails


class HistoricalDataManager:
    def __init__(self, broker_client: Any):
        """
        Initializes the HistoricalDataManager.

        Args:
            broker_client: An instance of a broker client (e.g., MockFyersClient or a live FyersClient).
                           It's typed as Any to allow flexibility for different client implementations
                           that adhere to a common interface for fetching historical data.
        """
        if broker_client is None:
            raise ValueError("Broker client cannot be None.")
        self.broker_client = broker_client
        print("HistoricalDataManager initialized.")

    def fetch_historical_data(self, symbol: str, timeframe: str, 
                              start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetches historical market data using the configured broker client.

        Args:
            symbol (str): The trading symbol (e.g., "SBIN-EQ").
            timeframe (str): The timeframe for the data (e.g., "1D", "5MIN"). 
                               (Should align with what the broker_client expects)
            start_date (datetime): The start date for the data.
            end_date (datetime): The end date for the data.

        Returns:
            Optional[pd.DataFrame]: A Pandas DataFrame containing the historical data
                                    (columns: timestamp, open, high, low, close, volume, symbol, timeframe),
                                    or None if data fetching fails.
        """
        if not hasattr(self.broker_client, 'get_historical_data'):
            print("Error: The provided broker client does not have a 'get_historical_data' method.")
            return None

        print(f"HistoricalDataManager: Requesting data for {symbol} from {start_date} to {end_date} via broker client.")
        
        try:
            data_df = self.broker_client.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )

            if data_df is not None and isinstance(data_df, list):
                if not data_df: # If the list is empty
                    # Create an empty DataFrame with expected columns if possible, 
                    # or handle as per existing logic for empty data.
                    # For now, let's convert to an empty DataFrame.
                    # Callers might expect certain columns even if empty.
                    data_df = pd.DataFrame(data_df) # This will create an empty DF if list is empty
                else:
                    data_df = pd.DataFrame(data_df)

            if data_df is not None and not data_df.empty:
                # Optional: Add further validation or processing here
                # e.g., ensure required columns are present, sort by date, etc.
                required_cols = ['timestamp', 'open', 'high', 'low', 'close']
                if not all(col in data_df.columns for col in required_cols):
                    print(f"Warning: Fetched data for {symbol} is missing one or more required columns: {required_cols}")
                    # Depending on strictness, could return None or try to adapt
                
                # Convert timestamp to datetime objects if they aren't already
                if 'timestamp' in data_df.columns and not pd.api.types.is_datetime64_any_dtype(data_df['timestamp']):
                     data_df['timestamp'] = pd.to_datetime(data_df['timestamp'])

                print(f"HistoricalDataManager: Successfully fetched {len(data_df)} bars for {symbol}.")
            elif data_df is not None and data_df.empty:
                print(f"HistoricalDataManager: Fetched no data for {symbol} for the given period (empty DataFrame returned).")
            else: # data_df is None
                print(f"HistoricalDataManager: Failed to fetch data for {symbol} (broker returned None).")

            return data_df

        except Exception as e:
            print(f"HistoricalDataManager: An error occurred while fetching data for {symbol}: {e}")
            return None

    def get_all_data_sorted_by_timestamp(self, symbols: list[str], timeframe: str,
                                         start_date: datetime, end_date: datetime) -> list[tuple[datetime, dict[str, Candle]]]:
        """
        Fetches historical data for multiple symbols, combines them, and sorts by timestamp.

        Args:
            symbols (list[str]): A list of trading symbols.
            timeframe (str): The timeframe for the data (e.g., "1D", "5MIN").
            start_date (datetime): The start date for the data.
            end_date (datetime): The end date for the data.

        Returns:
            list[tuple[datetime, dict[str, Candle]]]: A list of tuples, where each tuple contains:
                - A datetime object representing the timestamp.
                - A dictionary where keys are symbol strings and values are Candle objects for that timestamp.
              The list is sorted by timestamp in ascending order.
        """
        all_candles_by_timestamp = defaultdict(dict)
        
        # Convert timeframe string to Timeframe enum
        try:
            timeframe_enum = Timeframe(timeframe)
        except ValueError:
            # Attempt to map common timeframe strings to enum values if direct mapping fails
            # This is a basic example; a more robust solution might involve a comprehensive mapping dictionary
            if timeframe == "1D":
                timeframe_enum = Timeframe.DAY_1
            elif timeframe == "5MIN": # Example, adjust as per actual common inputs vs enum values
                timeframe_enum = Timeframe.MINUTE_5
            # Add more mappings as needed
            else:
                print(f"Warning: Timeframe string '{timeframe}' not directly mapped. Attempting fallback or default.")
                # Fallback or raise error if no suitable mapping found
                # For now, let's try to find a match by replacing "minute" with "MIN" etc. or use a default
                # This part needs to be robust based on expected timeframe string formats
                try:
                    # Example: "5minute" -> "5MINUTE" -> Timeframe.MINUTE_5 (if enum names are like MINUTE_5)
                    # This is highly dependent on enum naming and input string variations.
                    processed_tf_str = timeframe.upper() # Basic processing
                    if not processed_tf_str.startswith("MINUTE_") and "MINUTE" in processed_tf_str:
                         processed_tf_str = processed_tf_str.replace("MINUTE","MINUTE_")

                    timeframe_enum = Timeframe[processed_tf_str] # This requires exact match after processing
                except KeyError:
                    print(f"Error: Could not convert timeframe string '{timeframe}' to Timeframe enum. Please check mappings.")
                    # Default to None or raise an error, depending on desired strictness
                    # For this implementation, let's assume it might be set to None if conversion fails and Candle handles it
                    timeframe_enum = None # Or raise ValueError("Invalid timeframe string")

        for symbol in symbols:
            print(f"Fetching data for symbol: {symbol}")
            df = self.fetch_historical_data(symbol, timeframe, start_date, end_date)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    # Ensure timestamp is datetime object
                    ts = pd.to_datetime(row['timestamp'])
                    
                    candle = Candle(
                        timestamp=ts,
                        symbol=symbol, # Use the current symbol in loop
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=int(row['volume']) if 'volume' in row and pd.notna(row['volume']) else 0,
                        timeframe=timeframe_enum
                    )
                    all_candles_by_timestamp[ts][symbol] = candle
            else:
                print(f"No data fetched for symbol: {symbol}")

        # Sort by timestamp
        sorted_timestamps = sorted(all_candles_by_timestamp.keys())
        
        # Prepare the final list of tuples
        result = [(ts, all_candles_by_timestamp[ts]) for ts in sorted_timestamps]
        
        print(f"Processed and sorted data for {len(symbols)} symbols. Returning {len(result)} timestamp entries.")
        return result

# Example Usage (can be removed or commented out for production)
if __name__ == '__main__':
    # This example assumes fyers_client.py is in the accessible python path (e.g. same directory or installed)
    # For the full framework, imports will be relative to the algo_trading_framework.src
    
    # Need to make sure MockFyersClient can be imported.
    # This might require adjusting PYTHONPATH if running this script directly
    # or placing a copy of fyers_client.py (or a simplified version) in the same directory for this test.
    
    # Simplified MockFyersClient for direct script execution if full import fails
    class StandaloneMockFyersClient:
        def __init__(self, client_id, token, **kwargs): self.is_connected = False; print("StandaloneMockFyersClient used.") # Corrected attribute name
        def connect(self): self.is_connected = True; print("StandaloneMock connected."); return True # Corrected attribute name
        def get_historical_data(self, symbol, timeframe, start_date, end_date):
            if not self.is_connected: return None # Corrected attribute name
            print(f"StandaloneMock fetching {symbol} {timeframe} from {start_date} to {end_date}")
            dates = pd.date_range(start_date, end_date, freq='D')
            if not len(dates): return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol', 'timeframe'])
            return pd.DataFrame({
                'timestamp': dates,
                'open': [100 + i for i in range(len(dates))],
                'high': [105 + i for i in range(len(dates))],
                'low': [95 + i for i in range(len(dates))],
                'close': [102 + i for i in range(len(dates))],
                'volume': [1000 + i*10 for i in range(len(dates))],
                'symbol': symbol,
                'timeframe': timeframe
            })

    client_to_use = None
    if MockFyersClient:
        try:
            client_to_use = MockFyersClient(client_id="test_hd_client", token="test_hd_token")
            # Attempt to connect the full client if it initializes
            if hasattr(client_to_use, 'connect'):
                 client_to_use.connect()
        except Exception as e:
            print(f"Could not instantiate or connect full MockFyersClient: {e}. Falling back to standalone mock.")
            client_to_use = StandaloneMockFyersClient(client_id="test_hd_client", token="test_hd_token")
            client_to_use.connect() # Connect the standalone mock
    else:
        client_to_use = StandaloneMockFyersClient(client_id="test_hd_client", token="test_hd_token")
        client_to_use.connect() # Connect the standalone mock

    # Check connection status consistently
    connected_successfully = False
    if hasattr(client_to_use, 'is_connected') and client_to_use.is_connected:
        connected_successfully = True
    
    if connected_successfully:
        data_manager = HistoricalDataManager(broker_client=client_to_use)
        
        symbol_to_fetch = "INFY-EQ"
        start_dt = datetime(2023, 1, 15)
        end_dt = datetime(2023, 1, 20)
        tf = "1D"

        historical_data = data_manager.fetch_historical_data(symbol_to_fetch, tf, start_dt, end_dt)

        if historical_data is not None:
            print(f"\nSuccessfully fetched data for {symbol_to_fetch} via HistoricalDataManager:")
            print(historical_data.head())
        else:
            print(f"\nFailed to fetch data for {symbol_to_fetch} via HistoricalDataManager.")
    else:
        print("Could not connect mock client for HistoricalDataManager example.")

import pandas as pd
from datetime import datetime
from typing import Optional, Any
# Attempt to import the mock client, handling potential import errors gracefully for standalone use/testing.
try:
    from algo_trading_framework.src.broker_api.fyers_client import MockFyersClient
except ImportError:
    # This allows the file to be potentially run or imported in environments where the full structure isn't available,
    # though for framework operation, the correct path should resolve.
    # Fallback for direct testing or if paths are not yet perfectly set up.
    # A more robust solution in a large project might involve better PYTHONPATH handling or stub files.
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

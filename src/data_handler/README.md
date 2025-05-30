# Data Handler Module

The `data_handler` module is responsible for fetching, caching, and managing historical market data. It has been refactored to support a more flexible and extensible architecture for sourcing data.

## Core Components

1.  **`AbstractDataSource` (`abstract_data_source.py`)**
    *   An abstract base class that defines the contract for all data sources.
    *   Requires `fetch_data(symbol, start_date, end_date, timeframe)` to be implemented by concrete subclasses.
    *   Provides common utility methods:
        *   `validate_data(df)`: Validates if the DataFrame has the required columns (timestamp, ohlcv).
        *   `standardize_data(df)`: Standardizes data, ensuring 'timestamp' is `datetime64` and OHLCV columns are numeric.
        *   `adjust_for_splits(df)`: A placeholder for future stock split adjustments.

2.  **`CSVDataSource` (`csv_data_source.py`)**
    *   A concrete implementation of `AbstractDataSource` that fetches data from CSV files.
    *   It expects CSV files to be named in the format `{symbol}_{timeframe}.csv` (e.g., `SBIN-EQ_1D.csv`) and located in a specified directory.
    *   Handles loading data, filtering by date range, and utilizes the validation and standardization methods from `AbstractDataSource`.

3.  **`DataSourceFactory` (`data_source_factory.py`)**
    *   A factory class responsible for creating instances of various data sources.
    *   Currently supports creating `CSVDataSource` when the type "CSV" is requested.
    *   It can be extended to support other data source types (e.g., APIs) by adding new creation logic or registering new source creators.
    *   Example: `factory.get_data_source("CSV", csv_directory_path="/path/to/data")`

4.  **`DataCache` (`data_cache.py`)**
    *   An in-memory cache for storing Pandas DataFrames to reduce redundant data fetching.
    *   Uses a string key (typically generated from symbol, dates, timeframe, and source type) to store and retrieve DataFrames.
    *   Supports a maximum cache size with a FIFO (First-In, First-Out) eviction policy. If `max_size` is not set, the cache can grow indefinitely.

5.  **`HistoricalDataManager` (`historical_data_manager.py`)**
    *   The primary interface for accessing historical market data.
    *   It is initialized with a `DataSourceFactory` and a `DataCache`.
    *   **Workflow**:
        1.  When data is requested (e.g., via `fetch_historical_data(symbol, timeframe, start_date, end_date)`), it first generates a unique cache key.
        2.  It checks the `DataCache` for this key.
        3.  If data is found in the cache (cache hit), it's returned immediately.
        4.  If data is not in the cache (cache miss):
            *   It uses the `DataSourceFactory` to obtain an instance of the appropriate data source (e.g., `CSVDataSource` based on default or specified configuration).
            *   It calls `fetch_data` on the data source instance.
            *   The fetched DataFrame (if not empty) is then stored in the `DataCache` using the generated key.
            *   The DataFrame is returned.
    *   Provides `fetch_historical_data` for single-symbol data and `get_all_data_sorted_by_timestamp` for fetching, combining, and sorting data for multiple symbols into `Candle` objects.
    *   The `HistoricalDataManager` needs to be configured with a default data source type and its necessary arguments (e.g., `csv_directory_path` for `CSVDataSource`).

## Basic Usage Example

```python
from src.data_handler import HistoricalDataManager, DataSourceFactory, DataCache
from datetime import datetime

# 1. Initialize components
csv_data_path = "/path/to/your/csv_files" # Directory containing symbol_timeframe.csv files
factory = DataSourceFactory()
cache = DataCache(max_size=100) # Cache up to 100 DataFrames

# 2. Initialize HistoricalDataManager
hdm = HistoricalDataManager(
    data_source_factory=factory,
    data_cache=cache,
    default_source_type="CSV",
    default_source_kwargs={'csv_directory_path': csv_data_path}
)

# 3. Fetch data
symbol = "RELIANCE-EQ"
timeframe = "1D" # Daily data
start_date = datetime(2023, 1, 1)
end_date = datetime(2023, 12, 31)

data_df = hdm.fetch_historical_data(symbol, timeframe, start_date, end_date)

if not data_df.empty:
    print(f"Successfully fetched data for {symbol}:")
    print(data_df.head())
else:
    print(f"Could not fetch data for {symbol} or no data available.")

# Subsequent calls for the same parameters will likely hit the cache
data_df_cached = hdm.fetch_historical_data(symbol, timeframe, start_date, end_date)
# ...
```

This architecture makes the data handling system more modular, testable, and easier to extend with new data sources in the future.

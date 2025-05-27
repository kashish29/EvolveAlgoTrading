# Data Handler Module

The Data Handler module is responsible for sourcing, managing, and providing market data to other components of the trading framework, particularly for backtesting and strategy execution.

## `historical_data_manager.py`

The `HistoricalDataManager` class is the primary component of this module. Its key responsibilities include:

- **Fetching Historical Data:** It interfaces with a broker client (e.g., `MockFyersClient` or a live broker client) to retrieve historical candlestick data for specified instruments, timeframes, and date ranges.
- **Abstraction Layer:** It provides an abstraction layer over the broker-specific data fetching logic. This means that other parts of the system (like the backtester or strategies) can request data through a consistent interface, regardless of the underlying broker API being used.
- **Data Provision:** It supplies historical data, typically as Pandas DataFrames, to components that require it.

### Current Functionality:
- Initializes with a broker client instance.
- Provides a `fetch_historical_data` method that delegates the data request to the broker client.
- Includes basic error handling and logging for the data fetching process.

### Future Enhancements:
- **Caching:** Implement a caching mechanism (e.g., disk-based using Parquet or Feather files, or an in-memory cache) to store frequently accessed historical data, reducing redundant API calls and speeding up data retrieval.
- **Data Cleaning & Validation:** Add more robust data cleaning (e.g., handling missing values, correcting outliers if appropriate) and validation routines.
- **Multiple Data Sources:** Extend to support fetching data from multiple sources (e.g., different APIs, CSV files, databases) and consolidate them.
- **Real-time Data Feeds:** While named `HistoricalDataManager`, this module could be expanded or complemented by a real-time data handler for live trading.

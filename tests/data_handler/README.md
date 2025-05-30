# Data Handler Tests

This directory contains unit and integration tests for the components within the `src/data_handler` module.

## Test Structure

The tests are organized by the component they target:

*   **`test_abstract_data_source.py`**:
    *   (Note: As `AbstractDataSource` contains mostly abstract methods or simple concrete methods, its direct testing might be minimal. Its functionality is primarily tested through implementations like `CSVDataSource`.)
    *   If concrete utility methods in `AbstractDataSource` (like `validate_data`, `standardize_data`) have significant logic, they should have dedicated tests here. Currently, these are tested implicitly via `test_csv_data_source.py`.

*   **`test_csv_data_source.py`**:
    *   Unit tests for `CSVDataSource`.
    *   Mocks file system interactions (`os.path.exists`, `pd.read_csv`) to test:
        *   Successful data loading and parsing.
        *   Date filtering logic.
        *   Correct application of `standardize_data` and `validate_data`.
        *   Error handling for scenarios like file not found, empty CSVs, or malformed CSV data.

*   **`test_data_source_factory.py`**:
    *   Unit tests for `DataSourceFactory`.
    *   Ensures the factory correctly instantiates `CSVDataSource` when requested.
    *   Verifies that necessary arguments (e.g., `csv_directory_path`) are passed to the data source constructor.
    *   Tests behavior for unsupported source types or missing required arguments.

*   **`test_data_cache.py`**:
    *   Unit tests for `DataCache`.
    *   Covers:
        *   Storing and retrieving data (ensuring copies are returned).
        *   Cache hit and miss scenarios.
        *   Overwriting existing keys.
        *   Policies for handling empty or non-DataFrame data.
        *   FIFO eviction logic when `max_size` is set.
        *   Cache clearing functionality.

*   **`test_historical_data_manager.py`**:
    *   Unit tests for the refactored `HistoricalDataManager`.
    *   Mocks its dependencies (`DataSourceFactory`, `DataCache`, and `AbstractDataSource` instances).
    *   Tests:
        *   Cache hit logic (data source not called).
        *   Cache miss logic (data source called, data stored in cache).
        *   Correct interaction with the factory and data source.
        *   Handling of empty or error responses from the data source.
        *   Functionality of `get_all_data_sorted_by_timestamp`, including data aggregation, `Candle` object creation, sorting, and timeframe mapping.

*   **`test_integration_data_handling.py`**:
    *   Integration tests for the complete data handling pipeline.
    *   Uses a real (temporary) CSV file to test the flow:
        `HistoricalDataManager` -> `DataCache` -> `DataSourceFactory` -> `CSVDataSource`.
    *   Verifies scenarios:
        *   Cache miss: Data is fetched from the CSV file and populates the cache.
        *   Cache hit: Data is retrieved directly from the cache on subsequent identical requests.
        *   Data integrity: Ensures the DataFrame returned by `HistoricalDataManager` is correct and matches the data in the sample CSV.
        *   End-to-end functionality of `get_all_data_sorted_by_timestamp`.

## Running Tests

Tests can typically be run using Python's `unittest` module:

```bash
# Run all tests in the data_handler test directory
python -m unittest discover tests/data_handler

# Run a specific test file
python -m unittest tests.data_handler.test_historical_data_manager

# Run a specific test class
python -m unittest tests.data_handler.test_data_cache.TestDataCache

# Run a specific test method
python -m unittest tests.data_handler.test_data_cache.TestDataCache.test_store_and_get_data_success
```

Ensure that all dependencies required by the main application (like `pandas`) are installed in the test environment.

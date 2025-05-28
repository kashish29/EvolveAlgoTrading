# Live Trader Unit Tests (`tests/live_trader/`)

This directory contains unit tests for the components within the `src/live_trader/` module.
The tests aim to ensure the correctness of individual units of logic within the simulated live trading environment.

## Test Files:

-   **`test_event_handler.py`**: Contains unit tests for `EventHandler` and `DataFeedSimulator`.
    -   `TestDataFeedSimulator`:
        -   Tests the generation of market data events (`Candle`) from historical data.
        -   Tests the interaction with the `MockFyersClient` for setting the current bar, processing pending orders, and retrieving simulated order updates.
        -   Ensures that both market data and order update events are yielded correctly.
    -   `TestEventHandler`:
        -   Tests the main simulation loop.
        -   Verifies that market data events are correctly dispatched to the strategy's `on_bar` method.
        -   Verifies that order update events are correctly dispatched to the strategy's `on_order_update` method.
        -   Tests error handling within the event processing loop.

-   **`test_signal_processor.py`**: Contains unit tests for `SignalProcessor`.
    -   Tests signal processing logic with and without a (mocked) risk manager.
    -   Verifies that signals are forwarded to the `ExecutionHandler` if risk checks pass or no risk manager is present.
    -   Verifies that signals are not forwarded if risk checks fail.
    -   Tests logging for signal approval and rejection.

-   **`test_execution_handler.py`**: Contains unit tests for `ExecutionHandler`.
    -   Tests the conversion of `Signal` objects to `Order` objects for various order types (MARKET, LIMIT, STOP, STOP_LIMIT).
    -   Verifies that the `broker_client.place_order` method is called with a correctly formed `Order` object.
    -   Tests logging of order placement attempts and broker responses.
    -   Tests exception handling for errors raised by the broker client during order placement.

## Running Tests:

Tests can be run using the standard Python `unittest` module from the project root directory:

```bash
python -m unittest discover -s tests/live_trader
```

Or, if using a test runner like `pytest`:

```bash
pytest tests/live_trader/
```

**Note**: Due to unresolved issues with persistent `SyntaxError`s in some live trader source and test files (as of the last execution attempt), these tests may not run correctly until those underlying errors are fixed. The errors seem to prevent proper parsing of the files by the Python interpreter during test discovery.
```

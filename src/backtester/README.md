# Backtester Module (`src/backtester/`)

This module is responsible for simulating the execution of trading strategies against historical market data to evaluate their performance without risking real capital.

## Key Files:

### 1. `engine.py` - `BacktestingEngine`

-   **Engine Overview**:
    The `BacktestingEngine` is the core component of this module. Its primary function is to take a trading strategy, run it bar-by-bar against a historical dataset, simulate trade executions, and track portfolio performance over time.

-   **Workflow**:
    1.  **Initialization**:
        -   The engine is initialized with a strategy instance (which must be a subclass of `BaseStrategy` from `src/strategies/base_strategy.py`), a broker client instance (implementing `BaseBrokerClient` from `src/broker_api/base_broker_client.py`, e.g., `MockFyersClient`), historical market data (typically a list of `Candle` objects), initial capital, and any applicable commission rates.
    2.  **Data Iteration**:
        -   It iterates through the historical data one `Candle` (bar) at a time, representing the passage of time.
    3.  **Strategy Interaction (`on_bar`)**:
        -   For each `Candle`, the `BacktestingEngine` updates its internal state (e.g., current market price for the symbol being traded by the strategy).
        -   It then calls the strategy's `on_bar(current_bars)` method, passing the current bar's data (and potentially access to the history of bars if the strategy requires it, though direct provision of history is often handled by the strategy itself or data manager).
    4.  **Order Simulation (via Broker Client)**:
        -   If the strategy's `on_bar` method decides to issue a trade signal (e.g., by calling `self.broker.place_order()`), these orders are passed to the provided broker client instance.
        -   The broker client (e.g., `MockFyersClient`) simulates how these orders would be processed:
            -   `MARKET` orders might be filled at the current bar's prices (e.g., close or open).
            -   `LIMIT` orders are checked against the bar's price range to determine if they would have been filled.
            -   The broker client is responsible for updating the simulated portfolio (cash balance, positions) based on these fills and applying any commission costs.
    5.  **Portfolio Tracking**:
        -   Throughout the backtest, the `BacktestingEngine` (often with information from the broker client) tracks the value of the simulated portfolio (cash + value of open positions). This history is recorded for performance analysis.
    6.  **Liquidation (End of Backtest)**:
        -   At the end of the historical data, any remaining open positions in the simulated portfolio are typically liquidated at the last available market prices to calculate the final portfolio value and realize all profits or losses.
    7.  **Performance Metrics Calculation**:
        -   After the simulation is complete, the engine uses the `metrics.py` module to calculate a comprehensive set of performance statistics based on the portfolio history and the list of executed trades.

### 2. `metrics.py`

-   **Purpose**: This file contains functions dedicated to calculating various performance metrics from the results of a backtest.
-   **Inputs**: These functions typically take the portfolio value history (equity curve), the list of executed trades, and the initial capital as inputs.
-   **Calculated Metrics**:
    -   **Total Return (%)**: The overall percentage gain or loss on the initial capital.
    -   **Sharpe Ratio (Annualized)**: A measure of risk-adjusted return. (The implementation might specify assumptions, e.g., risk-free rate).
    -   **Sortino Ratio (Annualized)**: Similar to Sharpe Ratio but focuses only on downside volatility.
    -   **Maximum Drawdown (%)**: The largest percentage drop from a peak to a subsequent trough in the portfolio value, indicating the worst loss experienced.
    -   **Total Trades**: The total number of trades executed.
    -   **Winning Trades / Losing Trades / Win Rate (%)**: Statistics on the profitability of trades.
    -   **Profit Factor**: Gross profit divided by gross loss.
    -   Other metrics relevant to strategy performance.
-   **`calculate_all_metrics()` / `get_performance_summary()`**: Typically, a primary function in this module aggregates all individual metric calculations and returns them as a dictionary, providing a comprehensive performance report for the strategy.

This backtesting system allows for the iterative testing and refinement of trading strategies by providing quantitative feedback on their historical performance.

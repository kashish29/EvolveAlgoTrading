# Backtester Module

This module is responsible for simulating the execution of trading strategies on historical market data to evaluate their performance.

## `engine.py` - `BacktestEngine`

The `BacktestEngine` is the core component for running backtests.

### Initialization:
- Takes a strategy instance (derived from `BaseStrategy`), historical market data (Pandas DataFrame), initial capital, and commission per trade.
- Validates the historical data for required columns (`timestamp`, `open`, `high`, `low`, `close`, `symbol`).

### Workflow (`run()` method):
1.  **Iterates through Historical Data:** Processes each bar (candle) of the historical data chronologically.
2.  **Calls Strategy's `on_bar`:** For each bar, it provides the current candle data and the history of data *before* the current candle to the strategy's `on_bar` method.
3.  **Signal Processing:**
    - If the strategy returns a `Signal` object:
        - **Simulates Order Execution:**
            - `MARKET` orders are assumed to fill at the current bar's closing price.
            - `LIMIT` orders are checked against the current bar's high-low range for a potential fill (simplified logic: fills at open or limit price if range is met).
            - Calculates commission costs.
        - **Updates Portfolio:**
            - Adjusts cash based on the trade.
            - Updates the quantity and average entry price of the position for the traded symbol.
            - Records the `Trade` object, attempting to calculate realized P&L for trades that reduce or close a position.
4.  **Portfolio Value Tracking:** Calculates and records the total portfolio value (cash + value of open positions at current prices) at each time step.
5.  **Liquidation:** At the end of the data, automatically liquidates any open positions at the last available closing prices to realize final P&L.
6.  **Performance Summary:** Calls functions from `metrics.py` to calculate and return a dictionary of key performance indicators.

### Key Data Structures Tracked:
- `cash`: Current cash balance.
- `positions`: A dictionary mapping symbols to `Position` objects.
- `trades`: A list of all executed `Trade` objects.
- `portfolio_history`: A list of dictionaries tracking portfolio value and cash over time.

## `metrics.py`

This file contains functions to calculate various performance metrics based on the backtest results.

### Current Metrics:
- **Total Return (%)**: Overall percentage return on initial capital.
- **Sharpe Ratio (Annualized)**: Risk-adjusted return (simplified, assumes 0 risk-free rate).
- **Sortino Ratio (Annualized)**: Risk-adjusted return focusing on downside deviation.
- **Maximum Drawdown (%)**: Largest peak-to-trough percentage decline in portfolio value.
- **Total Trades**: Total number of simulated trades.
- **Win/Loss Ratio**: Ratio of profitable trades to losing trades (currently placeholder as `Trade` object needs explicit P&L). *This will be improved when `Trade` objects reliably store their realized P&L from the `BacktestEngine`.*

### `get_performance_summary()`
A helper function that takes the portfolio history, list of trades, and initial capital to compute and return a dictionary of all the above metrics.

---

This backtesting engine provides a basic framework. Future enhancements could include more sophisticated order execution simulation (slippage, fill probabilities), handling of more order types, more detailed commission models, and more advanced performance metrics.

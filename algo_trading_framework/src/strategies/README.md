# Strategies Module

This module contains the logic for various trading strategies. All strategies should inherit from the `BaseStrategy` class and implement its required methods.

## `base_strategy.py`

- **`BaseStrategy` (Abstract Class):**
  - Defines the common interface for all strategies.
  - Requires concrete strategies to implement the `on_bar(current_candle, historical_data)` method, which is called for each new market data bar (candle).
  - The `on_bar` method is responsible for analyzing data and returning a `Signal` object (from `core.models`) if a trading opportunity is identified.
  - Strategies are initialized with a name and a dictionary of parameters.
  - Includes a helper `update_historical_data` method and `get_historical_data_for_on_bar` which can be used by strategies or backtesting engines to manage data fed into `on_bar`.

## `example_strategy.py`

- **`ExampleMovingAverageCrossStrategy`:**
  - A simple demonstration strategy that inherits from `BaseStrategy`.
  - It uses two moving averages (short-term and long-term) of closing prices.
  - **Logic:**
    - Generates a BUY `Signal` when the short-term MA crosses above the long-term MA.
    - Generates a SELL `Signal` when the short-term MA crosses below the long-term MA.
  - **Parameters:** `short_window`, `long_window`, `symbol`.
  - This strategy illustrates how to manage basic state (previous MA values) and generate signals based on indicator calculations.

## `evolved/` Directory
This subdirectory is intended to store strategies that are generated or modified by AI processes, such as an evolutionary algorithm (AlphaEvolve-like). These might be saved as Python modules or in other formats.

---

Strategies in this module should focus purely on the signal generation logic. They receive market data and should output trading signals. Order management, risk checks, and broker interaction are handled by other components of the framework.

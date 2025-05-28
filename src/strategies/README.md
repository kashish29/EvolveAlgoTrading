# Strategies Module (`src/strategies/`)

This module contains the core components for defining and implementing trading strategies within the framework.

## Key Files & Concepts:

### 1. `base_strategy.py` - `BaseStrategy` (Abstract Base Class)

-   **Purpose**: The `base_strategy.py` file defines an abstract class named `BaseStrategy`. This class serves as the fundamental blueprint from which all specific trading strategies must inherit.
-   **Interface**: `BaseStrategy` defines a common interface and provides shared functionalities that all strategies can utilize. Key methods that subclasses are expected to implement or override include:
    -   **`__init__(self, strategy_id: str, broker: BaseBrokerClient, config: dict = None)`**: The constructor for initializing the strategy. It typically takes a unique `strategy_id`, an instance of a broker client (implementing `BaseBrokerClient`), and a configuration dictionary containing strategy-specific parameters (e.g., symbol, indicators parameters, timeframe).
    -   **`on_bar(self, current_bars: Dict[str, 'Candle'])`**: This is the core method called by the `BacktestingEngine` (or a live trading engine) for each new market data bar (candle). The strategy logic to make trading decisions (e.g., analyze data, generate signals, place orders via `self.broker`) is implemented here. `current_bars` is a dictionary where keys are symbols and values are `Candle` objects for the current timestamp.
-   **Shared Functionality**: `BaseStrategy` might also provide common helper methods or properties, such as a logger instance (`self.logger`).

### 2. Creating New Strategies

To develop a new custom trading strategy:
1.  Create a new Python file within the `src/strategies/` directory (or a relevant subdirectory).
2.  Define a new class that inherits from `BaseStrategy` (e.g., `class MyNewStrategy(BaseStrategy):`).
3.  Implement the `__init__` method to initialize any specific parameters, indicators, or state needed by your strategy. Remember to call `super().__init__(...)`.
4.  Implement the `on_bar` method. This is where you will define the logic for:
    *   Accessing current and historical price data (potentially using data managed by the strategy itself or provided through other means).
    *   Calculating indicator values.
    *   Making trading decisions based on your strategy rules.
    *   Placing, modifying, or canceling orders using the `self.broker` instance (e.g., `self.broker.place_order(...)`).

### 3. Strategy Template for `EvolutionaryEngine`

-   The `EvolutionaryEngine` (part of the `StrategyLab` module located in `src/strategy_lab/evolutionary_engine.py`) often uses a specific Python code string as a template for generating and evolving strategies. This template, typically named `DEFAULT_STRATEGY_TEMPLATE` within `evolutionary_engine.py`, is itself a complete strategy class that inherits from `BaseStrategy`.
-   This template is designed to include identifiable parameters that the `EvolutionaryEngine` can modify as "genes" during the evolutionary process. For example, lines like:
    ```python
    self.short_window = self.config.get("short_window", 10)
    self.long_window = self.config.get("long_window", 20)
    self.quantity = self.config.get("quantity", 100)
    ```
    These default values in the `config.get()` calls (or direct assignments like `self.short_window = 10`) are targeted by the `EvolutionaryEngine`'s mutation and crossover operators to create new strategy variations.

### 4. Example Strategies

-   **`example_moving_average_cross_strategy.py`**: This file provides a concrete example of a strategy (likely a moving average crossover system) implemented by inheriting from `BaseStrategy`. It serves as a practical illustration of how to structure a strategy class.
-   **`evolved/` directory**: This subdirectory is intended to store strategies that are generated or evolved by the `StrategyLab` module. The `StrategyGenerator` might save the code strings of promising or best-performing evolved strategies into this directory.

This modular approach to strategies allows for easy development, testing, and integration of diverse trading algorithms into the framework.

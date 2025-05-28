# Project Unit Tests

## Overview

This directory (`tests/`) contains all unit tests for the Algorithmic Trading Framework. The tests are written using Python's built-in `unittest` framework and are crucial for ensuring the reliability, correctness, and maintainability of the codebase.

The structure of the `tests/` directory mirrors the `src/` directory. For example, tests for `src/core/models.py` are located in `tests/core/test_models.py`.

## Running All Tests

To discover and run all unit tests, execute the following command from the project's root directory:

```bash
python -m unittest discover -s tests
```

This command will find all files matching the pattern `test_*.py` within the `tests` directory and its subdirectories.

## Test Modules:

*   **`tests/core/test_models.py`**:
    *   **Scope**: Tests for core data models defined in `src/core/models.py`, such as `Candle`, `Order`, `Trade`, and `Position`. It also covers event models like `SignalEvent`, `MarketEvent`, `OrderEvent`, and `FillEvent` if these are part of `models.py`. Verifies model initialization, attribute handling, and any specific methods associated with these data structures.

*   **`tests/broker_api/test_mock_fyers_client.py`**:
    *   **Scope**: Tests for the `MockFyersClient` located in `src/broker_api/mock_fyers_client.py`. Verifies simulated broker functionalities including order placement (market, limit), simulation of order modification/cancellation, position tracking, cash/balance updates, and the provisioning of mock historical data.

*   **`tests/backtester/test_engine.py`**:
    *   **Scope**: Tests for the `BacktestingEngine` from `src/backtester/engine.py`. Verifies the engine's main backtesting loop, correct iteration through historical data, proper calls to a strategy's `on_bar` method, interaction with a (mocked) broker client for order simulation, portfolio updates, and the accurate generation of performance results and metrics.

*   **`tests/strategy_lab/test_fitness_evaluator.py`**:
    *   **Scope**: Tests for the `FitnessEvaluator` from `src/strategy_lab/fitness_evaluator.py`. Verifies its ability to correctly take a strategy code string, manage its execution (typically via a mocked or real backtester instance), and accurately return the calculated fitness metrics.

*   **`tests/strategy_lab/test_evolutionary_engine.py`**:
    *   **Scope**: Tests for the `EvolutionaryEngine` from `src/strategy_lab/evolutionary_engine.py`. Covers key genetic algorithm functionalities: initialization of a strategy population (based on templates), parent selection mechanisms (e.g., tournament selection), crossover operations (e.g., parameter swapping in code strings), mutation operators (e.g., random changes to parameters), and the overall population evolution process, including elitism and handling of constraints (like `long_window > short_window`).

*   **`tests/strategy_lab/test_strategy_generator.py`**:
    *   **Scope**: Tests for the `StrategyGenerator` from `src/strategy_lab/strategy_generator.py`. Verifies the orchestration of the entire evolutionary workflow, ensuring correct calls to the `EvolutionaryEngine` for generating new populations and to the `FitnessEvaluator` for assessing strategy performance. It also tests the tracking of the best strategy across multiple generations and the handling of optional LLM refinement cycles.

*   **`tests/strategy_lab/test_llm_interface.py`**:
    *   **Scope**: Tests for `MockLLMInterface` (defined in `src/strategy_lab/llm_interface.py`) and serves as a placeholder for any future real LLM interface implementations. Verifies methods for strategy parsing, prompt generation, and code refinement logic.

*   **`tests/strategies/test_example_strategy.py`**:
    *   **Scope**: Tests for the `ExampleMovingAverageCrossStrategy` found in `src/strategies/example_moving_average_cross_strategy.py`. Verifies its signal generation logic based on moving average crossovers under various simulated market data scenarios to ensure it behaves as expected.

*   **`tests/analytics/`**:
    *   **Scope**: This directory is intended for tests related to the `src/analytics/` module. These tests would cover functionalities such as performance report generation (`performance_reporter.py`) and data visualization (`plotting.py`), ensuring metrics are calculated correctly and charts are generated as expected once these features are implemented. (Currently contains `__init__.py`).

*   **`tests/data_handler/`**:
    *   **Scope**: This directory is for tests of the `src/data_handler/` module, particularly `historical_data_manager.py`. Tests would verify data fetching logic, handling of different data formats, caching mechanisms (if implemented), and any data cleaning or validation processes. (Currently contains `__init__.py`).

*   **`tests/utils/`**:
    *   **Scope**: This directory is for tests of utility functions and classes found in `src/utils/`, such as `config_loader.py`, `datetime_utils.py`, and `logger.py`. Tests would ensure that configuration is loaded correctly, datetime manipulations are accurate, and logging is set up and functions as intended. (Currently contains `__init__.py`).

*   **`tests/live_trader/`**:
    *   **Scope**: Placeholder for tests of the `src/live_trader/` module components once they are developed (e.g., `EventHandler`, `SignalProcessor`, `ExecutionHandler`). (Currently contains `__init__.py`).

*   **`tests/risk_management/`**:
    *   **Scope**: Placeholder for tests of the `src/risk_management/` module components once they are developed (e.g., `RiskMonitor`, risk rule implementations). (Currently contains `__init__.py`).

This README serves as a guide to understanding the testing landscape of the project. Developers should add new tests here as new functionalities are introduced.

## Analytics Module Tests (`tests/analytics`)

Unit tests for the `PerformanceReporter` and other components of the Analytics module are located in the `tests/analytics/` directory. These tests ensure the correctness of performance metric calculations, report generation logic, and plotting functionalities.

*   **`tests/analytics/test_performance_reporter.py`**: Contains detailed unit tests for the `PerformanceReporter` class.
    *   See `tests/analytics/README.md` for more details on the testing strategy for this component.

Integration tests that verify the interaction between `BacktesterEngine` and `PerformanceReporter` can be found in `tests/backtester/test_engine_analytics_integration.py`.

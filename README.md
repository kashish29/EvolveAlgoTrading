# Algorithmic Trading Framework

This project is an algorithmic trading framework designed for developing, backtesting, deploying, and evolving trading strategies, with a focus on AI-driven strategy generation and refinement.

## Overall Architecture

The framework is composed of several key components:

*   **Data Handler**: Responsible for managing historical market data. (Future enhancements will include real-time data capabilities).
*   **Broker API**: Provides an interface for interacting with trading brokers.
    *   `BaseBrokerClient`: An abstract base class defining the common broker operations.
    *   `MockFyersClient`: A mock implementation for testing and development, simulating a broker like Fyers.
*   **Strategies**: Contains the `BaseStrategy` class that all trading strategies should inherit from, along with example strategy implementations.
*   **Backtester**: The `BacktestingEngine` evaluates the performance of trading strategies against historical market data, generating key performance metrics.
*   **StrategyLab**: A module dedicated to the automated generation and evolution of trading strategies. It consists of:
    *   `StrategyGenerator`: Orchestrates the overall evolutionary workflow, managing generations, evaluations, and (optionally) LLM refinement cycles.
    *   `EvolutionaryEngine`: Implements the genetic algorithm. This includes initializing a population of strategies (currently template-based), performing selection (e.g., tournament selection), crossover (e.g., parameter swapping within the strategy code), and mutation (e.g., random changes to parameters like `short_window`, `long_window`, `quantity` within the strategy code).
    *   `FitnessEvaluator`: Assesses the performance of candidate strategies. It utilizes the `Backtester` to run strategies against historical data and calculate fitness scores (e.g., Sharpe Ratio, Total Return).
    *   `LLMInterface`: An interface for incorporating Large Language Models into the strategy generation process. Currently, a `MockLLMInterface` is implemented, which simulates LLM responses for strategy refinement tasks without calling a real LLM.
*   **Analytics Module (`src/analytics`)**: Provides tools for in-depth performance analysis, report generation, and metrics calculation.
*   **Interaction**: The `StrategyLab`'s `FitnessEvaluator` directly uses the `Backtester` to run each candidate strategy and obtain performance metrics, which are then used as fitness scores to guide the `EvolutionaryEngine`.

## Current Status

The framework has the following features implemented:

*   **Core Infrastructure**:
    *   Basic data models for orders, candles, positions.
    *   Basic historical data handling.
    *   A functional backtesting engine (`BacktestingEngine`) capable of running strategies and producing performance reports.
    *   Abstract `BaseBrokerClient` and a `MockFyersClient` for simulated trading operations.
    *   `BaseStrategy` class for strategy development.
*   **StrategyLab**:
    *   `FitnessEvaluator` fully integrated with the `Backtester`.
    *   `EvolutionaryEngine` implementing template-based strategy representation. It evolves parameters (e.g., `short_window`, `long_window`, `quantity`) within a predefined strategy code structure using string/dictionary modifications. Selection, crossover, and mutation operators are functional.
    *   `StrategyGenerator` that successfully runs the evolutionary loop, managing populations across multiple generations.
    *   `MockLLMInterface` integrated for simulated strategy refinement cycles.
*   **Analytics Module**:
    *   `PerformanceReporter` class capable of generating HTML reports via `quantstats`, calculating key metrics, and plotting equity curves.
    *   Integration of `PerformanceReporter` into `BacktesterEngine` for automated report generation.
    *   Integration of `PerformanceReporter` metrics into `FitnessEvaluator` for comprehensive fitness assessment.
*   **Examples**:
    *   Example strategies demonstrating usage of the `BaseStrategy`.
*   **Testing**:
    *   Comprehensive unit tests for `StrategyLab` components: `EvolutionaryEngine`, `StrategyGenerator`, and `FitnessEvaluator`.
    *   Unit tests for other core components like the `BacktestingEngine` and data models.
    *   Unit tests for the `PerformanceReporter` in the Analytics module.

## Known Limitations

*   **Strategy Representation**: In the `EvolutionaryEngine`, strategies are currently represented as code templates. Evolution occurs by modifying parameters embedded as strings or within dictionary structures in this template, rather than evolving more complex structural aspects of the strategy logic itself.
*   **Genetic Operators**: The crossover and mutation operators in `EvolutionaryEngine` are currently simplified (e.g., parameter value swaps from strategy code strings, random parameter changes within the code).
*   **LLM Integration**: The LLM-based strategy refinement feature uses a `MockLLMInterface`. There is no integration with a real Large Language Model at this stage.
*   **Data Handling**: Data handling capabilities are currently basic, primarily focused on loading historical data from CSV files. Real-time data feeds and broader data source integration are not yet implemented.
*   **Risk Management**: A dedicated, comprehensive risk management module is not yet fully developed; current risk considerations are likely embedded within individual strategies or are basic.

## Analytics Module

The Analytics Module plays a crucial role in evaluating and understanding the performance of trading strategies. Its core component, `PerformanceReporter`, offers the following capabilities:

*   **Comprehensive Reporting**: Generates detailed HTML reports using `quantstats`, summarizing strategy performance with numerous charts and metrics (e.g., CAGR, Sharpe Ratio, Sortino Ratio, Max Drawdown, Calmar Ratio, volatility, win/loss statistics, and more).
*   **Key Metric Calculation**: Provides a standardized dictionary of key performance indicators (KPIs) crucial for assessing strategy viability.
*   **Visualizations**: Generates plots such as the equity curve (with optional benchmark comparison) and drawdown underwater charts.

**Integration:**

*   **Backtester (`src/backtester`)**: The `BacktesterEngine` utilizes the Analytics Module to automatically generate performance reports and equity curve plots after each backtest run. This allows for immediate visual and statistical feedback on strategy performance.
*   **Strategy Lab (`src/strategy_lab`)**: The `FitnessEvaluator` in the Strategy Lab uses the metrics calculated by the Analytics Module as the primary basis for determining the fitness of evolved or tested strategies. This ensures that strategy selection is driven by robust and comprehensive performance data.

## Roadmap/Next Steps

Future development will focus on:

*   **LLM Integration**: Integrate a real LLM for strategy refinement via the `LLMInterface`.
*   **Advanced EvolutionaryEngine**: Expand `EvolutionaryEngine` capabilities, including:
    *   More sophisticated genetic operators (e.g., tree-based genetic programming for strategy logic).
    *   Support for different and more complex strategy representations.
*   **Live Trader Module**: Develop a module for deploying and running strategies in a live trading environment.
*   **Risk Management**: Implement a comprehensive `Risk Management` module to apply risk rules across strategies and at the portfolio level.
*   **Enhanced Data Handling**: Improve data handling to include more data sources, data cleaning utilities, and real-time data feeds.
*   **Strategy Analysis**: Add more tools for analyzing strategy performance and characteristics.
*   **Expanded Strategy Library**: Develop and include a broader range of example strategies.

## How to Run

The primary way to run simulations or strategy generation is via `src/main.py`.

*   **To run the StrategyLab demo (evolutionary process):**
    ```bash
    python src/main.py --mode strategylab
    ```
*   **To run a Backtest demo with an example strategy:**
    (Assuming `main.py` supports a backtest mode and strategy configuration files)
    ```bash
    python src/main.py --mode backtest --strategy path/to/your_strategy_config.yaml 
    ```
    (Note: Specific command-line arguments for backtesting may vary based on `main.py` implementation.)

## Running Unit Tests

To run the suite of unit tests:

1.  Ensure all dependencies are installed (e.g., `pip install -r requirements.txt` if a requirements file is provided, or install `pandas` manually if not listed: `pip install pandas`).
2.  Navigate to the project root directory in your terminal.
3.  Run the following command:

    ```bash
    python -m unittest discover -s tests
    ```

This will discover and run all tests located in the `tests` directory.

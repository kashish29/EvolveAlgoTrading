# Strategy Lab Module (`src/strategy_lab/`)

The Strategy Lab module is dedicated to the AI-driven generation, evolution, evaluation, and refinement of trading strategies. It aims to automate parts of the strategy discovery process, drawing inspiration from concepts like genetic algorithms and potentially leveraging Large Language Models (LLMs) for code manipulation.

## Overview and Workflow

The Strategy Lab operates through the coordinated efforts of its main components: `StrategyGenerator`, `EvolutionaryEngine`, `FitnessEvaluator`, and an `LLMInterface` (currently implemented as `MockLLMInterface`).

The typical workflow is as follows:

1.  **Initialization**: The `StrategyGenerator` kicks off the process by instructing the `EvolutionaryEngine` to create an initial population of trading strategies.
2.  **Strategy Representation**:
    *   Strategies are represented as Python code strings.
    *   The `EvolutionaryEngine` often uses a base template, `DEFAULT_STRATEGY_TEMPLATE` (defined within `evolutionary_engine.py`), to generate these initial strategies. This template is a fully functional strategy class inheriting from `BaseStrategy`.
    *   Key parameters within this template (e.g., `self.short_window = self.config.get("short_window", 5)`, `self.long_window = ...`, `self.quantity = ...`) are treated as "genes." The `EvolutionaryEngine` modifies the values of these parameters directly within the code string during mutation and crossover.
3.  **Fitness Evaluation (Generational Loop)**:
    *   For each strategy (code string) in the current population, the `StrategyGenerator` tasks the `FitnessEvaluator` with assessing its performance.
    *   The `FitnessEvaluator` dynamically loads and executes the strategy code. It then utilizes the main `Backtester` engine (from `src/backtester/engine.py`) to run the strategy against historical market data.
    *   After the backtest, the `FitnessEvaluator` calculates a range of performance metrics (e.g., Sharpe Ratio, Total Return, Max Drawdown) using functionalities from `src/backtester/metrics.py`. These metrics form the "fitness score" of the strategy.
4.  **Evolution (Generational Loop)**:
    *   The `StrategyGenerator` collects the fitness scores for the entire population.
    *   It then passes the population (list of code strings) and their fitness scores to the `EvolutionaryEngine`.
    *   The `EvolutionaryEngine` applies genetic operators to produce the next generation of strategies:
        *   **Selection**: Parents are chosen from the current population based on their fitness (e.g., using tournament selection).
        *   **Crossover**: Selected parents are combined to create offspring strategies.
        *   **Mutation**: Offspring strategies may undergo random modifications.
5.  **LLM Refinement (Optional)**:
    *   After the evolutionary cycles, or potentially at intermediate stages, the `StrategyGenerator` can optionally use the `LLMInterface` (currently `MockLLMInterface`) to refine promising strategy codes.
    *   This involves sending the strategy code and a feedback prompt (e.g., based on its performance) to the LLM, which then (conceptually) returns a modified version of the code. The refined strategy is then re-evaluated.
6.  **Iteration**: Steps 3 (Evaluation) and 4 (Evolution) are repeated for a configured number of generations. The `StrategyGenerator` tracks the best-performing strategy found throughout this entire process.
7.  **Result**: Finally, the `StrategyGenerator` outputs the code of the overall best strategy and its associated fitness metrics.

## Evolutionary Operators (Current Implementation)

The `EvolutionaryEngine` currently implements the following simplified operators:

*   **Crossover ("Parameter Swap" Logic)**:
    *   When combining two parent strategy code strings, the offspring inherits parameters in a specific manner. For example, the offspring might receive its `short_window` and `quantity` values by parsing them from `parent1_code`, and its `long_window` value from `parent2_code`.
    *   **Constraint Handling**: The crossover logic includes checks to ensure basic strategy viability, such as `long_window` being greater than `short_window`. If a direct swap violates such constraints, parameters are adjusted (e.g., `long_window` is set to `short_window + 1` or capped at its maximum allowed value).
*   **Mutation ("Parameter Change" Logic)**:
    *   A random parameter within the strategy code string (e.g., `short_window`, `long_window`, or `quantity`) is chosen.
    *   Its value is changed to a new random integer selected from predefined ranges stored in `EvolutionaryEngine.param_ranges`.
    *   **Constraint Handling**: Similar to crossover, mutation logic ensures that constraints like `long_window > short_window` are maintained. If a random change violates this, the mutated value is adjusted to satisfy the constraint (e.g., `short_window` is capped at `current_long_window - 1`, or `long_window` is floored at `current_short_window + 1`). Values are also clamped within their global min/max ranges.

## Key Files & Components:

### `strategy_generator.py`
-   **`StrategyGenerator`**: Orchestrates the entire strategy evolution process. It coordinates the `EvolutionaryEngine` for population management and genetic operations, the `FitnessEvaluator` for assessing strategy performance, and the `LLMInterface` for optional refinement steps. It manages the main generational loop and tracks the overall best strategy.

### `evolutionary_engine.py`
-   **`EvolutionaryEngine`**: Implements the core genetic algorithm. It handles:
    -   Initialization of the strategy population using the `DEFAULT_STRATEGY_TEMPLATE`.
    -   Selection of parent strategies (e.g., tournament selection).
    -   Crossover of parent strategies (currently parameter swapping).
    -   Mutation of offspring strategies (currently random parameter changes).
-   **`DEFAULT_STRATEGY_TEMPLATE`**: A string variable within this file that defines the base Python code structure for strategies being evolved. It includes identifiable parameters that the engine modifies.

### `fitness_evaluator.py`
-   **`FitnessEvaluator`**: Responsible for evaluating the fitness of individual strategy code strings.
    -   It dynamically executes the strategy code.
    -   It uses the main `Backtester` engine (`src/backtester/engine.py`) to run the strategy against historical data.
    -   It calculates performance metrics using `src/backtester/metrics.py` to serve as fitness scores.

### `llm_interface.py`
-   **`MockLLMInterface`**: A mock implementation of the `LLMInterface`.
    -   It simulates interactions with a Large Language Model for tasks like refining strategy code based on feedback.
    -   Currently, its methods (`generate_strategy_code`, `refine_strategy_code`, `combine_strategy_codes`) return predefined or slightly modified versions of the input code/prompts, without actual LLM calls. This allows testing the integration points for future real LLM use.

This module aims to provide a flexible and extensible framework for experimenting with AI techniques in algorithmic trading strategy development.Okay, `src/strategy_lab/README.md` has been updated.

Next, I will update `src/broker_api/README.md`.
I'll first check if it exists and read its content.

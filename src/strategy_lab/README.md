# Strategy Lab Module (`src/strategy_lab/`)

The Strategy Lab module is dedicated to the AI-driven generation, evolution, and evaluation of trading strategies, inspired by concepts like AlphaEvolve. It aims to automate parts of the strategy discovery process.

**Note: The current implementations in this module are MOCKS.** They simulate the behavior of the intended components but do not perform real AI operations, LLM calls, or rigorous backtesting for fitness. They serve to establish the architectural flow.

## Components:

### `llm_interface.py`
- **`MockLLMInterface`:**
  - This class simulates interactions with a Large Language Model (LLM), providing a placeholder for future integration with actual AI-driven code generation and modification. All operations are currently mocked and do not involve real LLM calls.
  - **Methods:**
    - **`generate_initial_strategy(prompt: str) -> str`**:
      - *Intended Role*: To generate a base strategy code string based on a given `prompt`. This strategy would serve as an initial seed or template for the evolutionary process.
      - *Current Mock Implementation*: Ignores the `prompt` and returns a hardcoded strategy string (the `EvolvedStrategy` template, which is a moving average crossover strategy).
    - **`refine_strategy_code(code: str, feedback: str) -> str`**:
      - *Intended Role*: To simulate an LLM refining an existing strategy `code` string based on textual `feedback` (e.g., suggestions for improvement, error messages).
      - *Current Mock Implementation*: Appends the `feedback` as a Python comment to the end of the provided `code` string. It does not perform any actual code analysis or modification.
    - **`combine_strategy_codes(code_a: str, code_b: str, prompt: str) -> str`**:
      - *Intended Role*: To simulate an LLM combining two separate strategy code strings (`code_a`, `code_b`) into a single, potentially synergistic strategy, guided by a `prompt`.
      - *Current Mock Implementation*: Performs a simple string concatenation of `code_a` and `code_b`, separated by a comment indicating the mock combination and the guiding `prompt`.
  - **Overall Purpose:**
    - The `MockLLMInterface` defines the *intended interface* for how other components in the Strategy Lab (like `StrategyGenerator` or potentially `EvolutionaryEngine` in the future) would interact with an LLM.
    - In a real system, these methods would be replaced with actual calls to an LLM API, involving prompt engineering, sending code/feedback, and parsing the LLM's response to extract usable strategy code.

### `fitness_evaluator.py`
- **`FitnessEvaluator`:**
  - Acts as the bridge between AI-generated strategy code and the backtesting engine. It takes raw strategy code, runs it through a backtest, and returns comprehensive performance metrics.
  - **Primary Method:** `evaluate_strategy(self, strategy_code_string: str, historical_data_path: str, strategy_config: dict) -> dict`
    - **Inputs:**
      - `strategy_code_string (str)`: The Python code string of the trading strategy to be evaluated. The code should define a class named `EvolvedStrategy` or any class that inherits from `BaseStrategy`.
      - `historical_data_path (str)`: The file path to a CSV containing historical market data. The CSV must include 'timestamp', 'open', 'high', 'low', 'close', and 'volume' columns.
      - `strategy_config (dict)`: A dictionary providing configuration for the strategy. This must include:
        - `symbol (str)`: The trading symbol for the strategy (e.g., "SBIN-EQ").
        - It can also include other parameters required by the strategy (e.g., `short_window`, `long_window`, `timeframe`). The `timeframe` defaults to `Timeframe.DAY_1` if not specified.
    - **Outputs:**
      - On successful evaluation, it returns a dictionary containing various performance metrics calculated by `src/backtester/metrics.py`. These can include Sharpe ratio, Sortino ratio, maximum drawdown, total return percentage, number of trades, win rate, profit factor, etc.
      - In case of an error during any stage of evaluation (code execution, data loading, backtesting, metric calculation), the returned dictionary will contain an 'error' key with a descriptive message, and default pessimistic values for the metrics (e.g., `-float('inf')` for ratios, 0 for counts).
  - **Process Overview:**
    1.  **Dynamic Strategy Loading:** The `strategy_code_string` is executed using `exec()` to dynamically load the strategy class.
    2.  **Data Preparation:** Historical data is loaded from the specified CSV path using `pandas`, converted into `Candle` objects, and managed by the `HistoricalDataManager`.
    3.  **Backtester Setup:** A `MockFyersClient` (simulating broker interactions) and the `BacktesterEngine` are initialized. The dynamically loaded strategy is instantiated with its configuration and the broker.
    4.  **Backtest Execution:** The `BacktesterEngine` runs the strategy over the historical data.
    5.  **Metrics Calculation:** Post-backtest, performance metrics are computed using the `calculate_all_metrics` function based on the equity curve and trade log.

### `evolutionary_engine.py`
- **`EvolutionaryEngine`:**
  - Manages the population of trading strategies and applies evolutionary operators to generate new populations. It works with strategy code as strings and uses parameter manipulation for evolution.
  - **Primary Methods & Responsibilities:**
    - **`__init__(initial_strategy_template, llm_interface, primary_fitness_metric, tournament_size, elitism_count, mutation_probability)`**:
      - Initializes the engine. Key configurations include:
        - `initial_strategy_template (str)`: A template string for the strategy code (expected to define an `EvolvedStrategy` class).
        - `llm_interface`: Placeholder for a future LLM interface for advanced operations (currently not used by `EvolutionaryEngine`).
        - `primary_fitness_metric (str)`: The key to use in the fitness score dictionary for selection (e.g., "sharpe_ratio").
        - `tournament_size (int)`: Number of individuals in a selection tournament.
        - `elitism_count (int)`: Number of top individuals to carry over to the next generation.
        - `mutation_probability (float)`: Probability of an offspring undergoing mutation.
        - It also defines internal `param_ranges` for strategy parameters like `short_window`, `long_window`, and `quantity`.
    - **`initialize_population(size: int) -> List[str]`**:
      - Creates an initial population of `size` strategy code strings.
      - Each strategy is a copy of the `initial_strategy_template` with its parameters (`short_window`, `long_window`, `quantity`) randomized within predefined ranges, ensuring `long_window > short_window`.
    - **`select_parents(population: List[str], fitness_scores: List[Dict[str, Any]]) -> List[str]`**:
      - Implements parent selection using tournament selection. It repeatedly samples a subset of the population (tournament) and selects the individual with the best `primary_fitness_metric` from that subset.
    - **`crossover(parent1_code: str, parent2_code: str) -> str`**:
      - (Currently Simplified) Combines two parent strategies to produce an offspring.
      - The current implementation performs a one-point crossover by taking `short_window` and `quantity` from `parent1_code` and `long_window` from `parent2_code`. It ensures the `long_window > short_window` constraint in the offspring.
    - **`mutate(strategy_code: str) -> str`**:
      - (Currently Simplified) Makes small random changes to a strategy's parameters.
      - It randomly selects one parameter (`short_window`, `long_window`, or `quantity`) and assigns it a new random value within its defined range, again ensuring `long_window > short_window`.
    - **`evolve_population(population: List[str], fitness_scores: List[Dict[str, Any]]) -> List[str]`**:
      - Orchestrates the creation of a new generation.
      - It applies elitism (carrying over the best individuals), then uses `select_parents` to choose parents for the rest of the new population.
      - Offspring are generated via `crossover` and then may undergo `mutate` based on `mutation_probability`.
  - **Interactions & Current Nature:**
    - It receives the current population (list of strategy code strings) and their corresponding `fitness_scores` (list of dictionaries, typically from `FitnessEvaluator` via `StrategyGenerator`).
    - It outputs a new population (list of strategy code strings).
    - The `llm_interface` is not currently used by `EvolutionaryEngine` for crossover or mutation.
    - Crossover and mutation operators are currently simplified, focusing on manipulating numeric parameters (e.g., `short_window`, `long_window`, `quantity`) within the strategy code string using regular expressions. They do not yet perform structural code changes or utilize LLM guidance for more complex genetic operations.

### `strategy_generator.py`
- **`StrategyGenerator`:**
  - Orchestrates the entire strategy evolution process, coordinating the `EvolutionaryEngine`, `FitnessEvaluator`, and `MockLLMInterface` (though the LLM interface is not actively used in the current evolution loop).
  - **Primary Methods & Responsibilities:**
    - **`__init__(self, fitness_evaluator: FitnessEvaluator, evolutionary_engine: EvolutionaryEngine, llm_interface: MockLLMInterface, config: dict)`**:
      - Initializes the generator with instances of the other key Strategy Lab components: `FitnessEvaluator` and `EvolutionaryEngine`.
      - It also takes a `MockLLMInterface` (for potential future use in more advanced strategy generation/mutation).
      - A `config` dictionary is required, which must contain:
        - `historical_data_path (str)`: Path to the historical data CSV for the `FitnessEvaluator`.
        - `strategy_config_template (dict)`: A template dictionary for `FitnessEvaluator.evaluate_strategy()`, which must include `symbol` and can include other base parameters for the strategy.
        - `population_size (int)`: The number of strategies in each generation.
        - `num_generations (int)`: The number of generations the evolution process will run for.
    - **`run_evolution() -> Optional[Tuple[Optional[str], Optional[Dict[str, Any]]]]`**:
      - This is the main method that drives the evolutionary process.
      - **Workflow:**
        1.  **Initialization**: Creates an initial population of strategy code strings using `evolutionary_engine.initialize_population()`.
        2.  **Generational Loop**: Iterates for the configured `num_generations`. In each generation:
            a.  **Evaluation**: Each strategy code in the current population is evaluated by calling `fitness_evaluator.evaluate_strategy()`, passing the strategy code, `historical_data_path`, and `strategy_config_template`.
            b.  **Tracking & Logging**: The best strategy within the current generation (based on the `primary_fitness_metric` from `EvolutionaryEngine`) and its fitness metrics are logged. The overall best strategy found across all generations so far is also tracked.
            c.  **Evolution**: If not the last generation, the population is evolved by calling `evolutionary_engine.evolve_population()`, which uses the fitness scores from the evaluation step to select parents, perform crossover, and apply mutation, producing the next generation of strategy codes.
        3.  **Return Value**: After all generations are complete, it returns a tuple containing the code string of the best strategy found overall and its corresponding fitness metrics dictionary. If no strategy is found or an error occurs, it may return `(None, None)`.

## Workflow Overview:
The `StrategyGenerator` orchestrates the evolutionary cycle as follows:

1.  **Initial Population**: `StrategyGenerator` directs the `EvolutionaryEngine` to create an initial population of diverse strategy code strings. These strategies are typically variations of a base template with different parameter values. (The `MockLLMInterface` is available but not currently used by `EvolutionaryEngine` or `StrategyGenerator` for this step).
2.  **Fitness Evaluation (Loop)**: For each strategy in the current population, `StrategyGenerator` instructs the `FitnessEvaluator` to:
    a.  Load the strategy code.
    b.  Run a backtest using the historical data specified in `StrategyGenerator`'s configuration.
    c.  Calculate and return a dictionary of performance metrics.
3.  **Evolutionary Operations (Loop)**: Based on the fitness metrics received from `FitnessEvaluator`, `StrategyGenerator` tasks the `EvolutionaryEngine` to:
    a.  Select parent strategies (e.g., using tournament selection based on a primary metric like Sharpe ratio).
    b.  Generate offspring strategies through crossover and mutation operators. This forms the next generation's population.
4.  **Iteration**: Steps 2 and 3 are repeated for a configured number of generations. `StrategyGenerator` keeps track of the best-performing strategy found across all generations.
5.  **Result**: The `StrategyGenerator` outputs the best strategy code and its performance metrics found during the entire evolutionary process.

---
This structure provides a foundation for building a sophisticated AI-powered strategy discovery system. The `MockLLMInterface` remains a placeholder for future integration where an LLM could assist in generating initial strategies, or in more complex mutation/crossover operations within the `EvolutionaryEngine`.

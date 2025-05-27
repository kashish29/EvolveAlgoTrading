# Strategy Lab Module (`src/strategy_lab/`)

The Strategy Lab module is dedicated to the AI-driven generation, evolution, and evaluation of trading strategies, inspired by concepts like AlphaEvolve. It aims to automate parts of the strategy discovery process.

**Note: The current implementations in this module are MOCKS.** They simulate the behavior of the intended components but do not perform real AI operations, LLM calls, or rigorous backtesting for fitness. They serve to establish the architectural flow.

## Components:

### `llm_interface.py`
- **`MockLLMInterface`:**
  - Simulates interactions with a Large Language Model (LLM).
  - Provides methods like:
    - `generate_strategy_code(prompt)`: Returns a mock Python strategy code string based on a prompt.
    - `mutate_strategy_code(code, prompt)`: Returns a mock mutated version of the input strategy code.
    - `combine_strategy_codes(code_a, code_b, prompt)`: Returns a mock combination of two strategy codes.
  - In a real system, this would handle API calls, prompt engineering, and parsing LLM responses.

### `fitness_evaluator.py`
- **`MockFitnessEvaluator`:**
  - Simulates the evaluation of a strategy's performance (fitness).
  - Provides `evaluate_strategy(strategy_code_string)` which returns a mock fitness score (e.g., a random float).
  - A real fitness evaluator would:
    1.  Dynamically compile/load the `strategy_code_string`.
    2.  Instantiate the strategy.
    3.  Run it through the `BacktestEngine` with historical data and defined parameters.
    4.  Calculate actual performance metrics (Sharpe ratio, net profit, drawdown, etc.) to determine the fitness score.

### `evolutionary_engine.py`
- **`MockEvolutionaryEngine`:**
  - Simulates the core genetic algorithm (or other evolutionary computation) operators.
  - Provides methods for:
    - `select_parents(population, fitness_scores)`: Mock selection of parent strategies.
    - `crossover(parent1_code, parent2_code)`: Mock combination of parent strategies to produce offspring, potentially using the `MockLLMInterface`.
    - `mutate(strategy_code)`: Mock mutation of a strategy, potentially using the `MockLLMInterface`.
  - A real engine would implement robust selection mechanisms (e.g., tournament, roulette wheel), and more sophisticated crossover/mutation operators that preserve code validity and explore the strategy space effectively.

### `strategy_generator.py`
- **`StrategyGenerator`:**
  - Orchestrates the overall strategy evolution process using the other components.
  - `generate_initial_population()`: Uses the `MockLLMInterface` to create an initial set of strategies.
  - `_evaluate_current_population()`: Uses the `MockFitnessEvaluator` to assess the fitness of all strategies in the current population.
  - `run_evolution_cycle()`: Iteratively applies selection, crossover, and mutation (via `MockEvolutionaryEngine`) to evolve the population over several generations, re-evaluating fitness each time.
  - `get_best_strategy()`: Identifies the strategy with the highest fitness score from the current population.

## Workflow Overview (Simulated):
1.  `StrategyGenerator` calls `MockLLMInterface` to produce an initial population of strategy code strings.
2.  Each strategy code is passed to `MockFitnessEvaluator` to get a (random) fitness score.
3.  `StrategyGenerator` uses `MockEvolutionaryEngine` to:
    a.  Select promising strategies based on mock fitness.
    b.  Apply mock crossover and mutation (which might internally call `MockLLMInterface` again for code modifications).
4.  This creates a new generation of strategy codes.
5.  The process repeats, ideally leading to strategies with (randomly) higher fitness scores over generations.

---
This structure provides a foundation for building a sophisticated AI-powered strategy discovery system. Future work involves replacing mock components with real implementations.

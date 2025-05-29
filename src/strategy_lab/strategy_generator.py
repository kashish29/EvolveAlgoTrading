from typing import List, Dict, Any, Optional, Tuple
import logging
import pandas as pd
import os
import datetime

# Assuming these are the actual implemented classes
from .fitness_evaluator import FitnessEvaluator
from .evolutionary_engine import EvolutionaryEngine, DEFAULT_STRATEGY_TEMPLATE # Import template for test
from .llm_interface import MockLLMInterface # LLM remains mock for now


class StrategyGenerator:
    def __init__(self,
                 fitness_evaluator: FitnessEvaluator,
                 evolutionary_engine: EvolutionaryEngine,
                 llm_interface: MockLLMInterface, # Still mock
                 config: Dict[str, Any]):
        self.fitness_evaluator = fitness_evaluator
        self.evolutionary_engine = evolutionary_engine
        self.llm_interface = llm_interface # For potential future use, not actively used in run_evolution
        self.config = config # Expected keys: 'historical_data_path', 'strategy_config_template', 'population_size', 'num_generations'
        
        self.logger = logging.getLogger(__name__)
        # Configure logger if not already configured by a higher-level module
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Ensure required config keys are present
        required_keys = ['historical_data_path', 'strategy_config_template', 'population_size', 'num_generations']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required key in StrategyGenerator config: {key}")

    def run_evolution(self) -> Optional[Tuple[Optional[str], Optional[Dict[str, Any]]]]:
        population_size = self.config['population_size']
        num_generations = self.config['num_generations']
        historical_data_path = self.config['historical_data_path']
        # strategy_config_template is what FitnessEvaluator's evaluate_strategy expects for its 'strategy_config' argument.
        # It should contain 'symbol' and other necessary base parameters for the strategy being evaluated.
        strategy_config_template = self.config['strategy_config_template'] 

        self.logger.info(f"Starting evolution: {num_generations} generations, {population_size} population size.")

        # 1. Initialize population
        current_population_codes = self.evolutionary_engine.initialize_population(population_size)
        if not current_population_codes:
            self.logger.error("EvolutionaryEngine failed to initialize population.")
            return None, None

        best_strategy_overall_code: Optional[str] = None
        best_strategy_overall_fitness: Optional[Dict[str, Any]] = None
        # Ensure primary_metric from engine is valid, otherwise provide a default
        primary_metric = getattr(self.evolutionary_engine, 'primary_fitness_metric', 'sharpe_ratio')
        if not primary_metric : primary_metric = 'sharpe_ratio'


        for gen in range(num_generations):
            self.logger.info(f"--- Generation {gen + 1}/{num_generations} ---")
            
            current_fitness_scores: List[Dict[str, Any]] = []
            generation_best_fitness_value = -float('inf')
            generation_best_strategy_code = None
            generation_best_fitness_dict = None

            # 2. Evaluate Population
            self.logger.info(f"Evaluating {len(current_population_codes)} strategies...")
            for i, strategy_code in enumerate(current_population_codes):
                self.logger.debug(f"Evaluating strategy {i+1}/{len(current_population_codes)}")
                
                # The strategy_config_template is passed to every strategy evaluation.
                # FitnessEvaluator uses the 'symbol' from this config for data processing
                # and the strategy code itself contains the evolved parameters like windows.
                fitness_dict = self.fitness_evaluator.evaluate_strategy(
                    strategy_code_string=strategy_code,
                    historical_data_path=historical_data_path,
                    strategy_config=strategy_config_template 
                )
                current_fitness_scores.append(fitness_dict)
                
                current_metric_value = fitness_dict.get(primary_metric, -float('inf'))
                if not isinstance(current_metric_value, (int,float)) or current_metric_value != current_metric_value: # Handles NaN
                    current_metric_value = -float('inf')


                if current_metric_value > generation_best_fitness_value:
                    generation_best_fitness_value = current_metric_value
                    generation_best_strategy_code = strategy_code
                    generation_best_fitness_dict = fitness_dict

            self.logger.info(f"Generation {gen + 1} best {primary_metric}: {generation_best_fitness_value:.4f}")
            
            if generation_best_strategy_code and generation_best_fitness_dict:
                 self.logger.debug(f"Generation {gen+1} best strategy details: {generation_best_fitness_dict}")
                 current_overall_best_value = -float('inf')
                 if best_strategy_overall_fitness:
                     val = best_strategy_overall_fitness.get(primary_metric, -float('inf'))
                     if isinstance(val, (int,float)) and val == val : # not NaN
                         current_overall_best_value = val

                 if generation_best_fitness_value > current_overall_best_value:
                    best_strategy_overall_code = generation_best_strategy_code
                    best_strategy_overall_fitness = generation_best_fitness_dict
                    self.logger.info(f"New overall best strategy found in generation {gen+1} with {primary_metric}: {generation_best_fitness_value:.4f}")

            if not current_fitness_scores: 
                self.logger.error("No fitness scores evaluated for the current population. Aborting.")
                return best_strategy_overall_code, best_strategy_overall_fitness

            # 3. Evolve Population
            self.logger.info("Evolving population for next generation...")
            if gen < num_generations - 1: # No need to evolve for the last generation
                current_population_codes = self.evolutionary_engine.evolve_population(
                    current_population_codes,
                    current_fitness_scores
                )
                if not current_population_codes:
                    self.logger.error("EvolutionaryEngine returned an empty population. Aborting.")
                    return best_strategy_overall_code, best_strategy_overall_fitness

        self.logger.info("Evolution finished.")
        if best_strategy_overall_code and best_strategy_overall_fitness:
            overall_best_val = best_strategy_overall_fitness.get(primary_metric, -float('inf'))
            if not isinstance(overall_best_val, (int,float)) or overall_best_val != overall_best_val: overall_best_val = -float('inf')
            self.logger.info(f"Best strategy overall ({primary_metric}: {overall_best_val:.4f}):")
            # self.logger.info(f"Code:\n{best_strategy_overall_code}") # Can be too verbose
            self.logger.info(f"Fitness Metrics: {best_strategy_overall_fitness}")
            return best_strategy_overall_code, best_strategy_overall_fitness
        else:
            self.logger.warning("No best strategy found after evolution.")
            return None, None

if __name__ == '__main__':
    print("--- StrategyGenerator Test ---")

    # 1. Create Dummy CSV
    dummy_csv_path = "dummy_ohlcv_strategy_generator.csv"
    dummy_data = {
        'timestamp': pd.to_datetime([
            datetime.datetime(2023, 1, 1, 9, 15) + datetime.timedelta(days=i) for i in range(20) # 20 days for enough data
        ]),
        'symbol': ['DUMMY_SYM'] * 20,
        'open': [100 + i*0.1 for i in range(20)],
        'high': [101 + i*0.2 for i in range(20)],
        'low': [99 - i*0.1 for i in range(20)],
        'close': [100.5 + i*0.15 for i in range(20)],
        'volume': [1000 + i*10 for i in range(20)]
    }
    dummy_df = pd.DataFrame(dummy_data)
    dummy_df.to_csv(dummy_csv_path, index=False)
    print(f"Created dummy CSV: {dummy_csv_path}")

    # 2. Instantiate components
    mock_llm = MockLLMInterface()
    
    # Use the imported DEFAULT_STRATEGY_TEMPLATE
    evo_engine = EvolutionaryEngine(
        initial_strategy_template=DEFAULT_STRATEGY_TEMPLATE,
        primary_fitness_metric="sharpe_ratio", # Example, can be any key from FitnessEvaluator output
        tournament_size=2,
        elitism_count=1,
        mutation_probability=0.1
    )
    
    fitness_eval = FitnessEvaluator(config={"initial_cash": 100000, "commission_rate": 0.001})

    # 3. Create StrategyGenerator config
    generator_config = {
        'historical_data_path': dummy_csv_path,
        'strategy_config_template': { # Base config for FitnessEvaluator
            'symbol': 'DUMMY_SYM', 
            'timeframe': '1D', # Example, FitnessEvaluator uses this if strategy needs it
            # These params in strategy_config_template are default starting points for the strategy's __init__
            # but EvolutionaryEngine will embed specific, evolved values directly into the strategy code string.
            'short_window': 5, 
            'long_window': 10
        },
        'population_size': 5, # Small for quick test
        'num_generations': 2   # Small for quick test
    }
    print(f"StrategyGenerator config: {generator_config}")

    # 4. Instantiate StrategyGenerator
    strategy_gen = StrategyGenerator(
        fitness_evaluator=fitness_eval,
        evolutionary_engine=evo_engine,
        llm_interface=mock_llm,
        config=generator_config
    )
    print("StrategyGenerator instantiated.")

    # 5. Run evolution
    print("Running evolution...")
    best_code: Optional[str]
    raw_best_fitness: Optional[Dict[str, Any]]
    evolution_result = strategy_gen.run_evolution()
    if evolution_result is not None:
        best_code, raw_best_fitness = evolution_result
    else:
        best_code, raw_best_fitness = None, None
    best_fitness: Dict[str, Any] = raw_best_fitness if raw_best_fitness is not None else {}

    # 6. Print results
    if best_code and best_fitness is not None:
        print("\n--- Evolution Complete ---")
        print(f"Best Strategy Fitness ({evo_engine.primary_fitness_metric}): {best_fitness.get(evo_engine.primary_fitness_metric, 'N/A')}")
        print("Best Strategy Metrics:")
        for k, v in best_fitness.items():
            print(f"  {k}: {v}")
        # print("Best Strategy Code:")
        # print(best_code) # Can be very verbose
    else:
        print("\n--- Evolution Complete ---")
        print("No successful strategy found or an error occurred.")

    # 7. Clean up dummy CSV
    try:
        os.remove(dummy_csv_path)
        print(f"Cleaned up dummy CSV: {dummy_csv_path}")
    except OSError as e:
        print(f"Error removing dummy CSV {dummy_csv_path}: {e}")
    
    print("--- StrategyGenerator Test Complete ---")

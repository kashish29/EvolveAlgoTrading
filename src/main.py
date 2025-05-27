import logging
import os
import pandas as pd
from datetime import datetime, timedelta
import random # For dummy data generation

from algo_trading_framework.src.strategy_lab.fitness_evaluator import FitnessEvaluator
from algo_trading_framework.src.strategy_lab.evolutionary_engine import EvolutionaryEngine, DEFAULT_STRATEGY_TEMPLATE
from algo_trading_framework.src.strategy_lab.llm_interface import MockLLMInterface
from algo_trading_framework.src.strategy_lab.strategy_generator import StrategyGenerator
from algo_trading_framework.src.core.enums import Timeframe

# Configure basic logging for the main script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_dummy_ohlcv_data(file_path: str, symbol: str, days: int = 60) -> None:
    if os.path.exists(file_path):
        # print(f"Dummy data file {file_path} already exists.")
        return

    logger.info(f"Creating dummy OHLCV data at {file_path} for symbol {symbol}...")
    start_date = datetime(2023, 1, 1)
    data = []
    base_price = 100
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        open_price = base_price + (i * 0.1) + random.uniform(-0.5, 0.5)
        high_price = open_price + random.uniform(0, 2)
        low_price = open_price - random.uniform(0, 2)
        close_price = open_price + random.uniform(-1, 1)
        volume = random.randint(1000, 10000)
        data.append([current_date.strftime('%Y-%m-%d %H:%M:%S'), symbol, open_price, high_price, low_price, close_price, volume])
    
    df = pd.DataFrame(data, columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
    df.to_csv(file_path, index=False)
    logger.info(f"Dummy data created successfully with {len(df)} rows.")

def run_strategy_lab_demo():
    print("\n" + "="*50)
    print("Running Strategy Lab Demonstration")
    print("="*50 + "\n")

    # Configuration
    dummy_data_symbol = "DUMMY_SLAB_SYM"
    dummy_data_file = "dummy_slab_ohlcv.csv"
    # Create data with enough history for typical MA calculations (e.g., 50-day MA needs more than 50 data points)
    create_dummy_ohlcv_data(dummy_data_file, dummy_data_symbol, days=70) 

    # Initialize StrategyLab components
    logger.info("Initializing StrategyLab components...")
    llm_interface = MockLLMInterface()
    # EvolutionaryEngine uses DEFAULT_STRATEGY_TEMPLATE by default if not provided in constructor
    evolutionary_engine = EvolutionaryEngine(initial_strategy_template=DEFAULT_STRATEGY_TEMPLATE) 
    fitness_evaluator = FitnessEvaluator() # Default config is usually fine

    # StrategyGenerator configuration
    generator_config = {
        "historical_data_path": dummy_data_file,
        "strategy_config_template": { # Passed to FitnessEvaluator for each strategy
            "symbol": dummy_data_symbol,
            "timeframe": Timeframe.DAY_1.value, # Ensure data matches this timeframe
            # Base parameters for the EvolvedStrategy's config.get() if not set by evolution in code
            "short_window": 7,  # This is a default, evolved code will have its own
            "long_window": 15, # This is a default, evolved code will have its own
            "quantity": 1 
        },
        "population_size": 10, # Keep small for demo; e.g., 20-50 for more serious runs
        "num_generations": 3   # Keep small for demo; e.g., 10-20 for more serious runs
    }
    logger.info(f"StrategyGenerator configured with: {generator_config['population_size']} population, {generator_config['num_generations']} generations.")

    strategy_generator = StrategyGenerator(
        fitness_evaluator=fitness_evaluator,
        evolutionary_engine=evolutionary_engine,
        llm_interface=llm_interface,
        config=generator_config
    )

    # Run the evolution
    logger.info("Starting StrategyLab evolution process...")
    best_result = strategy_generator.run_evolution()

    if best_result and best_result[0] and best_result[1]:
        best_code, best_fitness_metrics = best_result
        print("\n" + "-"*50)
        print("Strategy Lab Evolution Complete!")
        print("-"*50)
        # Use primary_fitness_metric from the engine instance for consistency
        primary_metric_name = evolutionary_engine.primary_fitness_metric
        primary_metric_value = best_fitness_metrics.get(primary_metric_name, 'N/A')
        
        if isinstance(primary_metric_value, float):
             print(f"Best strategy found with {primary_metric_name}: {primary_metric_value:.4f}")
        else:
            print(f"Best strategy found with {primary_metric_name}: {primary_metric_value}")

        print("Best Strategy Fitness Metrics:")
        for metric, value in best_fitness_metrics.items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.4f}")
            else:
                print(f"  {metric}: {value}")
        # print("\nBest Strategy Code Snippet (first 500 chars):")
        # print(best_code[:500] + "...") # Optional: print part of the code
    else:
        print("\nStrategy Lab Evolution did not yield a best strategy or encountered an error.")

    # Clean up dummy file - Enabled
    if os.path.exists(dummy_data_file):
        try:
            os.remove(dummy_data_file)
            logger.info(f"Cleaned up dummy data file: {dummy_data_file}")
        except OSError as e:
            logger.error(f"Error removing dummy data file {dummy_data_file}: {e}")
    
    print("\n" + "="*50)
    print("Strategy Lab Demonstration Finished")
    print("="*50 + "\n")

if __name__ == "__main__":
    logger.info("Starting main execution...")
    # Since the original main.py content for backtester demo is unknown/missing,
    # this main block will only run the Strategy Lab Demo.
    # If there was other content, it would need to be merged manually.
    
    run_strategy_lab_demo()
    
    logger.info("Main execution finished.")

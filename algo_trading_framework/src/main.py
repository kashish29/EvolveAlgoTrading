# algo_trading_framework/src/main.py

from datetime import datetime, timedelta
import pandas as pd
import os # For path joining
import logging # Added for potential direct logger level setting

# Core components
from algo_trading_framework.src.core.models import Candle # Used by Backtester
from algo_trading_framework.src.core.enums import TradeType # Used by Strategy & Backtester

# Broker API (Mock)
from algo_trading_framework.src.broker_api.fyers_client import MockFyersClient

# Data Handler
from algo_trading_framework.src.data_handler.historical_data_manager import HistoricalDataManager

# Strategies
from algo_trading_framework.src.strategies.example_strategy import ExampleMovingAverageCrossStrategy

# Backtester
from algo_trading_framework.src.backtester.engine import BacktestEngine

# Utilities
from algo_trading_framework.src.utils.config_loader import load_config
from algo_trading_framework.src.utils.logger import get_logger

# Strategy Lab (Mock Components)
from algo_trading_framework.src.strategy_lab.llm_interface import MockLLMInterface
from algo_trading_framework.src.strategy_lab.fitness_evaluator import MockFitnessEvaluator
from algo_trading_framework.src.strategy_lab.evolutionary_engine import MockEvolutionaryEngine
from algo_trading_framework.src.strategy_lab.strategy_generator import StrategyGenerator

# --- Configuration ---
# Get the directory of the current script to build relative paths
# Correct BASE_DIR to point to the 'algo_trading_framework' directory if main.py is in 'src'
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__)) # .../algo_trading_framework/src
BASE_DIR = os.path.dirname(CURRENT_FILE_DIR) # .../algo_trading_framework
CONFIG_DIR = os.path.join(BASE_DIR, "config") # .../algo_trading_framework/config/
STRATEGY_CONFIG_PATH = os.path.join(CONFIG_DIR, "strategy_params", "example_strategy.yaml")


# --- Setup Logger ---
main_logger = get_logger(__name__, log_level=logging.INFO) # Set default level to INFO for main script

def run_example_backtest():
    """
    Runs a backtest for the ExampleMovingAverageCrossStrategy using mock data.
    """
    main_logger.info("--- Starting Example Strategy Backtest ---")

    # 1. Initialize Mock Broker Client
    mock_broker = MockFyersClient(client_id="main_demo_client", token="main_demo_token")
    if not mock_broker.connect():
        main_logger.error("Failed to connect mock broker for backtest. Exiting backtest demo.")
        return

    # 2. Initialize Data Handler
    data_manager = HistoricalDataManager(broker_client=mock_broker)

    # 3. Fetch Mock Historical Data
    symbol = "MOCK_XYZ-EQ" 
    timeframe = "1D" 
    end_date = datetime.now()
    start_date = end_date - timedelta(days=200) 

    main_logger.info(f"Fetching mock historical data for {symbol} from {start_date.date()} to {end_date.date()}...")
    historical_df = data_manager.fetch_historical_data(symbol, timeframe, start_date, end_date)

    if historical_df is None or historical_df.empty:
        main_logger.error(f"Failed to fetch mock historical data for {symbol}. Exiting backtest demo.")
        return
    main_logger.info(f"Successfully fetched {len(historical_df)} bars of mock data.")

    # 4. Load Strategy Configuration
    try:
        strategy_params_full = load_config(STRATEGY_CONFIG_PATH)
        strategy_constructor_params = {
            "short_window": strategy_params_full.get("short_window", 10),
            "long_window": strategy_params_full.get("long_window", 20),
            "symbol": symbol 
        }
        strategy_name = strategy_params_full.get("strategy_name", "ExampleMovingAverageCross")

    except FileNotFoundError:
        main_logger.warning(f"Strategy config file not found at {STRATEGY_CONFIG_PATH}. Using default parameters.")
        strategy_constructor_params = {"short_window": 10, "long_window": 20, "symbol": symbol}
        strategy_name = "ExampleMovingAverageCross_Default"
    except Exception as e:
        main_logger.error(f"Failed to load or parse strategy configuration from {STRATEGY_CONFIG_PATH}: {e}")
        main_logger.warning("Using default parameters for ExampleMovingAverageCrossStrategy.")
        strategy_constructor_params = {"short_window": 10, "long_window": 20, "symbol": symbol}
        strategy_name = "ExampleMovingAverageCross_Default"


    # 5. Initialize Strategy
    main_logger.info(f"Initializing strategy '{strategy_name}' with params: {strategy_constructor_params}")
    example_strategy = ExampleMovingAverageCrossStrategy(
        strategy_name=strategy_name,
        params=strategy_constructor_params
    )

    # 6. Initialize Backtest Engine
    initial_capital = 100000.0
    commission_per_trade = 0.05 
    main_logger.info(f"Initializing BacktestEngine with initial capital ${initial_capital:,.2f} "
                     f"and commission ${commission_per_trade:.2f} per unit.")
    backtester = BacktestEngine(
        strategy_instance=example_strategy,
        historical_data=historical_df, 
        initial_capital=initial_capital,
        commission_per_trade=commission_per_trade
    )

    # 7. Run Backtest
    main_logger.info("Starting backtest run...")
    performance_summary = backtester.run()

    # 8. Print Performance Summary
    main_logger.info("--- Backtest Performance Summary ---")
    if performance_summary:
        for key, value in performance_summary.items():
            if isinstance(value, float):
                main_logger.info(f"{key}: {value:,.2f}")
            else:
                main_logger.info(f"{key}: {value}")
    else:
        main_logger.error("Backtest did not return a performance summary.")
    
    main_logger.info("--- End of Example Strategy Backtest ---")


def demonstrate_strategy_lab():
    """
    Demonstrates the mock functionality of the Strategy Lab components.
    """
    main_logger.info("\n--- Starting Strategy Lab Demonstration ---")

    # 1. Initialize Mock Components
    llm_interface = MockLLMInterface(model_name="demo_llm_v0.1")
    fitness_evaluator = MockFitnessEvaluator()
    evolutionary_engine = MockEvolutionaryEngine(llm_interface=llm_interface) 

    # 2. Initialize Strategy Generator
    strategy_generator = StrategyGenerator(
        llm_interface=llm_interface,
        fitness_evaluator=fitness_evaluator,
        evolutionary_engine=evolutionary_engine,
        population_size=3 
    )

    # 3. Generate Initial Population
    main_logger.info("Generating initial strategy population using MockLLMInterface...")
    strategy_generator.generate_initial_population(
        base_prompt="Develop a breakout strategy for volatile tech stocks."
    )
    
    main_logger.info("\nInitial Population (Code Snippets & Mock Fitness):")
    if strategy_generator.current_population_codes and strategy_generator.current_fitness_scores:
        for i, code in enumerate(strategy_generator.current_population_codes):
            # Check if index is within bounds for fitness_scores
            if i < len(strategy_generator.current_fitness_scores):
                 fitness = strategy_generator.current_fitness_scores[i]
                 main_logger.info(f"Strategy {i+1} (Fitness: {fitness:.2f}):\n{code[:200]}...\n")
            else:
                 main_logger.warning(f"Strategy {i+1} code found, but missing fitness score.")
    else:
        main_logger.warning("No initial population or fitness scores were generated/available.")

    # 4. Run a Mock Evolution Cycle
    num_mock_generations = 1 
    main_logger.info(f"\nRunning mock evolution for {num_mock_generations} generation(s)...")
    strategy_generator.run_evolution_cycle(num_generations=num_mock_generations)

    # 5. Get and Display the "Best" Strategy Found (based on mock fitness)
    main_logger.info("\n--- Mock Best Strategy from Strategy Lab ---")
    best_strategy_info = strategy_generator.get_best_strategy()
    if best_strategy_info:
        best_code, best_fitness = best_strategy_info
        main_logger.info(f"Best strategy code (mock fitness: {best_fitness:.2f}):")
        main_logger.info(best_code) 
    else:
        main_logger.warning("Could not determine a 'best' strategy from the mock lab.")

    main_logger.info("--- End of Strategy Lab Demonstration ---")


if __name__ == "__main__":
    main_logger.info("===== Algorithmic Trading Framework Demonstration =====")
    
    # Create dummy config if it doesn't exist to prevent FileNotFoundError on first run
    if not os.path.exists(STRATEGY_CONFIG_PATH):
        main_logger.warning(f"Strategy config {STRATEGY_CONFIG_PATH} not found. Creating a dummy one for demo.")
        if not os.path.exists(os.path.dirname(STRATEGY_CONFIG_PATH)):
            os.makedirs(os.path.dirname(STRATEGY_CONFIG_PATH))
        dummy_cfg_content = {
            "strategy_name": "ExampleMovingAverageCrossFromDummy",
            "short_window": 12,
            "long_window": 22,
            "symbol": "MOCK_DUMMY-EQ" # This will be overridden by `symbol` in run_example_backtest
        }
        try:
            with open(STRATEGY_CONFIG_PATH, 'w') as f:
                import yaml # Temporary import for this setup
                yaml.dump(dummy_cfg_content, f)
            main_logger.info(f"Dummy config created at {STRATEGY_CONFIG_PATH}")
        except Exception as e:
            main_logger.error(f"Could not create dummy config: {e}")


    run_example_backtest()
    
    main_logger.info("\n" + "="*50 + "\n")
    
    demonstrate_strategy_lab()
    
    main_logger.info("\n===== End of Demonstration =====")

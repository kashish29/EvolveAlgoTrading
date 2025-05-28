import datetime
import logging
import os
import pandas as pd
import random  # For dummy data generation
from datetime import datetime, timedelta

# Assuming project structure src/data, src/core, etc.
# Adjusted import path for HistoricalDataManager
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.broker_api.mock_fyers_client import MockFyersClient
from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
from src.backtester.engine import BacktesterEngine
from src.core.models import Candle, Timeframe  # OrderSide, OrderType are used within strategy/broker

from src.strategy_lab.fitness_evaluator import FitnessEvaluator
from src.strategy_lab.evolutionary_engine import EvolutionaryEngine, DEFAULT_STRATEGY_TEMPLATE
from src.strategy_lab.llm_interface import MockLLMInterface
from src.strategy_lab.strategy_generator import StrategyGenerator

# Basic Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Ensure logs go to console
    ]
)

# Configure basic logging for the main script
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
    print("\n" + "=" * 50)
    print("Running Strategy Lab Demonstration")
    print("=" * 50 + "\n")

    # Configuration
    dummy_data_symbol = "DUMMY_SLAB_SYM"
    dummy_data_file = "dummy_slab_ohlcv.csv"
    create_dummy_ohlcv_data(dummy_data_file, dummy_data_symbol, days=70)

    logger.info("Initializing StrategyLab components...")
    llm_interface = MockLLMInterface()
    evolutionary_engine = EvolutionaryEngine(initial_strategy_template=DEFAULT_STRATEGY_TEMPLATE)
    fitness_evaluator = FitnessEvaluator() 

    generator_config = {
        "historical_data_path": dummy_data_file,
        "strategy_config_template": { 
            "symbol": dummy_data_symbol,
            "timeframe": Timeframe.DAY_1.value, 
            "short_window": 7, 
            "long_window": 15, 
            "quantity": 1
        },
        "population_size": 10, 
        "num_generations": 3 
    }
    logger.info(f"StrategyGenerator configured with: {generator_config['population_size']} population, {generator_config['num_generations']} generations.")

    strategy_generator = StrategyGenerator(
        fitness_evaluator=fitness_evaluator,
        evolutionary_engine=evolutionary_engine,
        llm_interface=llm_interface,
        config=generator_config
    )

    logger.info("Starting StrategyLab evolution process...")
    best_result = strategy_generator.run_evolution()

    if best_result and best_result[0] and best_result[1]:
        best_code, best_fitness_metrics = best_result
        print("\n" + "-" * 50)
        print("Strategy Lab Evolution Complete!")
        print("-" * 50)
        primary_metric_name = evolutionary_engine.primary_fitness_metric
        primary_metric_value = best_fitness_metrics.get(primary_metric_name, 'N/A')

        if isinstance(primary_metric_value, float):
            print(f"Best strategy found with {primary_metric_name}: {primary_metric_value:.4f}")
        else:
            print(f"Best strategy found with {primary_metric_name}: {primary_metric_value}")

        # Enhanced logging for key metrics
        logger.info("Detailed performance metrics for the best strategy (from Analytics Module):")
        key_metrics_to_log = {
            "Sharpe Ratio": ".4f",
            "Max Drawdown [%]": ".2f", # Assuming it's a percentage
            "Total Return [%]": ".2f", # Assuming it's a percentage
            "Win Rate [%]": ".2f", # Assuming it's a percentage
            "Profit Factor": ".2f"
        }
        for metric_name, fmt_spec in key_metrics_to_log.items():
            metric_val = best_fitness_metrics.get(metric_name)
            if metric_val is not None:
                try:
                    # Attempt to format if it's a number, otherwise convert to string
                    if isinstance(metric_val, (int, float)):
                        logger.info(f"  {metric_name}: {metric_val:{fmt_spec}}")
                    else:
                         logger.info(f"  {metric_name}: {str(metric_val)}") # Handle non-numeric gracefully
                except (ValueError, TypeError):
                    logger.info(f"  {metric_name}: {metric_val} (Could not format)") # Log raw value if formatting fails
            else:
                logger.info(f"  {metric_name}: N/A")
        
        print("\nFull Fitness Metrics Set:") # Changed header for clarity
        for metric, value in best_fitness_metrics.items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.4f}")
            else:
                print(f"  {metric}: {value}")
    else:
        print("\nStrategy Lab Evolution did not yield a best strategy or encountered an error.")

    if os.path.exists(dummy_data_file):
        try:
            os.remove(dummy_data_file)
            logger.info(f"Cleaned up dummy data file: {dummy_data_file}")
        except OSError as e:
            logger.error(f"Error removing dummy data file {dummy_data_file}: {e}")

    print("\n" + "=" * 50)
    print("Strategy Lab Demonstration Finished")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    logger = logging.getLogger(__name__) 

    symbol = "SBIN_NSE"
    start_date = datetime.datetime(2023, 1, 1)
    end_date = datetime.datetime(2023, 1, 31) 
    data_timeframe = Timeframe.DAY_1
    initial_cash = 100000.0
    commission_rate_broker = 0.0007  

    logger.info(f"Setting up backtest for {symbol} from {start_date.date()} to {end_date.date()} with {data_timeframe.value} timeframe.")

    sample_candles: list[Candle] = []
    current_date = start_date
    days_generated = 0
    base_open = 100.0
    while current_date <= end_date and days_generated < 31: 
        open_price = base_open + days_generated * 0.5
        close_price = base_open + days_generated * 0.5 - (days_generated % 5) + 2  
        if days_generated > 10 and days_generated < 20:  
            close_price = base_open + days_generated * 0.5 - (days_generated % 3) - 5
        if days_generated > 20:  
            close_price = base_open + days_generated * 0.5 + (days_generated % 2) + 3

        sample_candles.append(Candle(
            timestamp=current_date, symbol=symbol, open=open_price, high=open_price + 2.0, 
            low=open_price - 2.0, close=close_price, volume=10000 + days_generated * 100,
            timeframe=data_timeframe
        ))
        current_date += datetime.timedelta(days=1)
        days_generated += 1

    if not sample_candles:
        logger.error("No sample candles generated. Exiting.")
        exit()

    data_feeds = {symbol: sample_candles}
    logger.info(f"Generated {len(sample_candles)} sample candles for {symbol}.")

    hdm = HistoricalDataManager()
    hdm.load_data(data_feeds)  

    broker = MockFyersClient(
        historical_data=hdm, initial_cash=initial_cash, commission_rate=commission_rate_broker
    )
    broker.connect()  

    strategy_config = {
        "symbol": symbol, "short_window": 5, "long_window": 10,
        "quantity": 10, "timeframe": data_timeframe 
    }
    strategy = ExampleMovingAverageCrossStrategy(
        strategy_id="MA_Cross_1", broker=broker, config=strategy_config
    )

    engine = BacktesterEngine(
        strategy=strategy,
        broker=broker,
        historical_data_manager=hdm,
        symbols=[symbol], # Corrected from symbols_to_trade to symbols
        timeframe=data_timeframe.value, 
        start_date=start_date,
        end_date=end_date,
        generate_analytics_report=True # Explicitly set for clarity
    )

    logger.info("Starting backtest engine...")
    equity_curve, portfolio_history = engine.run()
    logger.info("Backtest engine finished.")

    if equity_curve:
        logger.info(f"Final Portfolio Value: {equity_curve[-1]:.2f}")
    else:
        logger.info(f"Final Portfolio Value (no trades or activity): {initial_cash:.2f}")

    logger.info("Trade Log:")
    trade_log = broker.get_trade_history()  
    if trade_log:
        for trade in trade_log:
            trade_info = (
                f"TradeID: {trade.get('trade_id')}, OrderID: {trade.get('order_id')}, Symbol: {trade.get('symbol')}, "
                f"Side: {trade.get('side')}, Qty: {trade.get('quantity')}, Price: {trade.get('price', 0.0):.2f}, "
                f"Comm: {trade.get('commission', 0.0):.2f}, TS: {trade.get('timestamp')}"
            )
            logger.info(f"  {trade_info}")
    else:
        logger.info("  No trades executed.")

    logger.info("Portfolio History Snapshots (last 5):")
    for snapshot in portfolio_history[-5:]:
        snap_info = (
            f"TS: {snapshot.get('timestamp')}, Cash: {snapshot.get('cash', 0.0):.2f}, "
            f"PositionsVal: {snapshot.get('positions_market_value', 0.0):.2f}, TotalVal: {snapshot.get('total_value', 0.0):.2f}"
        )
        logger.info(f"  {snap_info}")
        for sym, pos_details in snapshot.get('positions', {}).items():
            logger.info(f"    {sym}: Qty={pos_details.get('qty')}, AvgP={pos_details.get('avg_price', 0.0):.2f}, LastP={pos_details.get('last_price', 0.0):.2f}, MktVal={pos_details.get('market_value', 0.0):.2f}")

    run_strategy_lab_demo()

    broker.disconnect() 
    logger.info("Main execution finished.")

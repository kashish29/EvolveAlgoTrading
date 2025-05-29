import logging
import os
import pandas as pd
import random  # For dummy data generation
from datetime import datetime, timedelta
import uuid

# Assuming project structure src/data, src/core, etc.
# Adjusted import path for HistoricalDataManager
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.broker_api.mock_fyers_client import MockFyersClient
from src.strategies.base_strategy import BaseStrategy # Added for DemoSignalStrategy
from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
from src.backtester.engine import BacktesterEngine
# Core models needed for main, backtesting, and live sim demo
from src.core.models import Candle, Timeframe, Signal, Order, OrderSide, OrderType, OrderStatus, Trade

# Live Trader Components
from src.live_trader.event_handler import EventHandler, DataFeedSimulator
from src.live_trader.signal_processor import SignalProcessor
from src.live_trader.execution_handler import ExecutionHandler

from src.strategy_lab.fitness_evaluator import FitnessEvaluator
from src.strategy_lab.evolutionary_engine import EvolutionaryEngine, DEFAULT_STRATEGY_TEMPLATE
from src.strategy_lab.llm_interface import MockLLMInterface
from src.strategy_lab.strategy_generator import StrategyGenerator
from typing import List, Dict, Any,Optional
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

# For DemoSignalStrategy type hints
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from src.broker_api.base_broker_client import BaseBrokerClient


def create_dummy_ohlcv_data(file_path: str, symbol: str, days: int = 60) -> None:
    if os.path.exists(file_path):
        # print(f"Dummy data file {file_path} already exists.")
        return

    logger.info(f"Creating dummy OHLCV data at {file_path} for symbol {symbol}...")
    start_date = datetime(2023, 1, 1)
    data = []
    base_price = 100.0 # Changed to float
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        # Introduce more significant price fluctuations to encourage crossovers
        price_change = random.uniform(-5, 5) # Larger random changes
        base_price += price_change
        open_price = base_price + random.uniform(-1, 1)
        high_price = open_price + abs(random.uniform(0, 3)) # Ensure high >= open
        low_price = open_price - abs(random.uniform(0, 3))  # Ensure low <= open
        close_price = open_price + random.uniform(-2, 2) # Close can be anywhere
        
        # Ensure prices are positive
        open_price = max(1.0, open_price)
        high_price = max(open_price, high_price) # High must be at least open
        low_price = min(open_price, low_price)   # Low must be at most open
        close_price = max(1.0, close_price)

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
        "population_size": 4,
        "num_generations": 2
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


# --- Demo Strategy for Live Simulation ---
class DemoSignalStrategy(BaseStrategy):
    def __init__(self, strategy_id: str, broker: 'BaseBrokerClient', config: Optional[dict[Any, Any]] = None, signal_processor: Optional['SignalProcessor'] = None):
        super().__init__(strategy_id, broker, config)
        self.signal_processor = signal_processor
        self.bars_processed = 0
        self.logger.info(f"DemoSignalStrategy '{strategy_id}' initialized. SignalProcessor: {'YES' if signal_processor else 'NO'}")

    # EventHandler passes broker_client, so signature should match
    def on_bar(self, current_bars: Dict[str, 'Candle']):
        self.bars_processed += 1
        current_bar_key = list(current_bars.keys())[0] # Assuming single symbol for demo
        current_bar = current_bars[current_bar_key]
        self.logger.info(f"Strategy {self.strategy_id} processing bar {self.bars_processed} for {current_bar.symbol} @ {current_bar.timestamp}: C={current_bar.close}")
        
        if self.bars_processed == 2:
            signal = Signal(
                timestamp=current_bar.timestamp,
                symbol=current_bar.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10,
                # No price or stop_price for MARKET order
                comment="Demo Buy Signal from on_bar"
            )
            self.logger.info(f"Strategy '{self.strategy_id}' generated BUY signal: {signal}")
            if self.signal_processor:
                self.signal_processor.process_signal(signal, current_portfolio_state={}) # Empty portfolio state for demo
            else:
                self.logger.warning("No signal_processor in strategy, falling back to direct order placement (if implemented).")
                # Fallback: self.broker.place_order(self.create_order_from_signal(signal)) - Requires create_order_from_signal

        elif self.bars_processed == 4:
            signal = Signal(
                timestamp=current_bar.timestamp,
                symbol=current_bar.symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=5,
                comment="Demo Sell Signal from on_bar"
            )
            self.logger.info(f"Strategy '{self.strategy_id}' generated SELL signal: {signal}")
            if self.signal_processor:
                self.signal_processor.process_signal(signal, current_portfolio_state={})
            else:
                self.logger.warning("No signal_processor in strategy, falling back to direct order placement (if implemented).")
                # Fallback: self.broker.place_order(self.create_order_from_signal(signal))

    # Helper to convert signal to order if strategy needs to fallback (not used if signal_processor is primary)
    def create_order_from_signal(self, signal: Signal) -> Order:
        return Order(
            id=str(uuid.uuid4()), # Generate a unique ID for the order
            symbol=signal.symbol,
            quantity=int(signal.quantity) if signal.quantity is not None else 0, # Ensure quantity is int, handle None
            side=signal.side,
            order_type=signal.order_type,
            price=signal.price, # Will be None for MARKET
            trigger_price=signal.stop_price, # Will be None for MARKET/LIMIT
            timestamp=datetime.now(), # Or signal.timestamp
            status=OrderStatus.PENDING_OPEN # Default status
        )

    def on_order_update(self, order_update: 'Order'):
        self.logger.info(f"Strategy {self.strategy_id} received order update: ID {order_update.id}, Status {order_update.status}")

    def on_fill(self, trade_event: 'Trade'): # trade_event is 'Trade'
        self.logger.info(f"Strategy {self.strategy_id} received fill: TradeID {trade_event.trade_id}, OrderID {trade_event.order_id}, Qty {trade_event.quantity} @ {trade_event.price}")


def run_live_simulation_demo():
    logger.info("\n" + "=" * 50)
    logger.info("Running Live Trading Simulation Demonstration")
    logger.info("=" * 50 + "\n")

    # a. Setup Parameters
    symbol = "SIM_STOCK"
    # Create a sample DataFrame for historical_data
    data = {
        'timestamp': pd.to_datetime(['2023-01-01 09:15:00', '2023-01-01 09:16:00', '2023-01-01 09:17:00', 
                                    '2023-01-01 09:18:00', '2023-01-01 09:19:00', '2023-01-01 09:20:00']),
        'symbol': [symbol] * 6,
        'open': [100, 101, 102, 101, 103, 104],
        'high': [100.5, 101.5, 102.5, 101.5, 103.5, 104.5],
        'low': [99.5, 100.5, 101.5, 100.5, 102.5, 103.5],
        'close': [101, 102, 101, 103, 104, 103],
        'volume': [1000, 1200, 1100, 1500, 1300, 1400],
        # Ensure Timeframe.MINUTE_1 is used correctly. Timeframe enum values are typically strings e.g. "1minute"
        # The Candle object expects a Timeframe enum member.
        'timeframe': [Timeframe.MINUTE_1] * 6 
    }
    historical_df = pd.DataFrame(data)
    
    initial_cash = 100000.0
    commission_rate_broker = 0.0007

    logger.info(f"Simulating for {symbol} with {len(historical_df)} data points using {Timeframe.MINUTE_1.value} timeframe.")

    # b. Instantiate Components
    logger.info("Instantiating components for live simulation...")
    
    # 1. Mock Broker Client
    # MockFyersClient's historical_data param expects a dict mapping symbol to a list of Candle objects,
    # or an object with a get_historical_candles method (like HistoricalDataManager).
    # For live sim, DataFeedSimulator provides bars, so broker might not need extensive history upfront.
    mock_broker = MockFyersClient(
        historical_data={}, # Empty, as DataFeedSimulator will provide bars
        initial_cash=initial_cash,
        commission_rate=commission_rate_broker
    )
    mock_broker.connect()

    # 2. Execution Handler
    execution_handler = ExecutionHandler(broker_client=mock_broker)

    # 3. Signal Processor (No risk manager for this demo)
    signal_processor = SignalProcessor(execution_handler=execution_handler, risk_manager=None)
    
    # 4. Strategy
    # Instantiate the demo strategy, passing the signal_processor
    strategy_config = {"symbol": symbol, "timeframe_value": Timeframe.MINUTE_1.value} # Pass timeframe value
    demo_strategy = DemoSignalStrategy(
        strategy_id="DemoSignalStrategy_LIVE_1",
        broker=mock_broker, # BaseStrategy still needs a broker for other potential uses
        config=strategy_config,
        signal_processor=signal_processor # Pass signal_processor here
    )
    
    # 5. DataFeedSimulator
    # DataFeedSimulator default_symbol and default_timeframe are fallbacks if not in DataFrame.
    # Our DataFrame includes 'symbol' and 'timeframe' columns.
    data_feed_simulator = DataFeedSimulator(
        historical_data=historical_df,
        mock_broker=mock_broker,
        default_symbol=symbol, # Fallback
        default_timeframe=Timeframe.MINUTE_1 # Fallback
    )

    # 6. EventHandler
    event_handler = EventHandler(
        strategy=demo_strategy,
        broker_client=mock_broker, # EventHandler passes this to strategy.on_bar
        data_feed_simulator=data_feed_simulator
    )

    # c. Run Simulation Loop
    logger.info("Starting live simulation loop...")
    try:
        event_handler.run_simulation_loop()
    except Exception as e:
        logger.error(f"Error during simulation loop: {e}", exc_info=True)
    logger.info("Live simulation loop finished.")

    # d. Print Results
    logger.info("\n" + "-" * 20 + " Live Simulation Results " + "-" * 20)
    logger.info(f"Final Cash: {mock_broker.get_balance()['cash']:.2f}")
    
    logger.info("Positions:")
    positions = mock_broker.get_positions()
    if positions:
        for pos_data in positions: # MockFyersClient.get_positions returns list of dicts
            logger.info(f"  Symbol: {pos_data['symbol']}, Qty: {pos_data['quantity']}, Avg Price: {pos_data.get('average_price', 0):.2f}, Last Price: {pos_data.get('last_price', 0):.2f}")
    else:
        logger.info("  No open positions.")

    logger.info("Trade Log:")
    trade_log = mock_broker.get_trade_history()
    if trade_log:
        for trade in trade_log:
            trade_info = (
                f"  TradeID: {trade.get('trade_id')}, OrderID: {trade.get('order_id')}, Symbol: {trade.get('symbol')}, "
                f"Side: {trade.get('side')}, Qty: {trade.get('quantity')}, Price: {trade.get('price', 0.0):.2f}, "
                f"Comm: {trade.get('commission', 0.0):.2f}, TS: {trade.get('timestamp')}"
            )
            logger.info(trade_info)
    else:
        logger.info("  No trades executed.")
    
    logger.info("All Orders Log:")
    all_orders = mock_broker.get_order_history() # Returns list of Order objects
    if all_orders:
        for order_obj in all_orders: 
            order_type_val = getattr(order_obj, 'order_type', 'N/A')
            order_side_val = getattr(order_obj, 'side', 'N/A')
            order_details = (
                f"  OrderID: {getattr(order_obj, 'id', 'N/A')}, Symbol: {getattr(order_obj, 'symbol', 'N/A')}, "
                f"Type: {order_type_val.value if hasattr(order_type_val, 'value') else order_type_val}, "
                f"Side: {order_side_val.value if hasattr(order_side_val, 'value') else order_side_val}, "
                f"Qty: {getattr(order_obj, 'quantity', 0)}, Price: {getattr(order_obj, 'price', 'N/A')}, "
                f"TrigPx: {getattr(order_obj, 'trigger_price', 'N/A')}, Status: {getattr(order_obj, 'status', 'N/A')}"
            )
            logger.info(order_details)
    else:
        logger.info("  No orders recorded in history.")

    mock_broker.disconnect()
    logger.info("Live Trading Simulation Demonstration Finished.\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 50)
    print("Running End-to-End Backtesting Workflow with Analytics")
    print("=" * 50 + "\n")

    # --- Backtester Demo Parameters ---
    test_symbol = "DEFAULT_SYMBOL" # Symbol used in test_data.csv
    test_data_file = "test_data/test_data.csv"
    
    # Load data from CSV
    logger.info(f"Loading historical data from {test_data_file}...")
    df = pd.read_csv(test_data_file, parse_dates=['timestamp'])
    
    # Determine start_date, end_date, and timeframe from loaded data
    start_date_backtest = df['timestamp'].min()
    end_date_backtest = df['timestamp'].max()
    # Assuming 1-minute data based on the CSV content and previous context
    data_timeframe_backtest = Timeframe.MINUTE_1

    initial_cash_backtest = 100000.0
    commission_rate_backtest = 0.0002 # 0.02%
    slippage_percent_backtest = 0.0001 # 0.01%

    logger.info(f"Setting up backtest for {test_symbol} from {start_date_backtest} to {end_date_backtest} with {data_timeframe_backtest.value} timeframe.")

    # Convert DataFrame to dictionary of Candle objects for MockFyersClient
    # The CSV doesn't have a 'symbol' column, so we'll assume the test_symbol for all candles.
    data_feeds: Dict[str, List[Candle]] = {test_symbol: []}
    for _, row in df.iterrows():
        candle = Candle(
            symbol=test_symbol,
            timestamp=row['timestamp'],
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume'],
            timeframe=data_timeframe_backtest # Assign the determined timeframe
        )
        data_feeds[test_symbol].append(candle)

    # Initialize MockFyersClient with the prepared data_feeds
    broker_for_backtest = MockFyersClient(
        historical_data=data_feeds, # Pass the converted data here
        initial_cash=initial_cash_backtest,
        commission_rate=commission_rate_backtest,
        slippage_percent=slippage_percent_backtest
    )
    broker_for_backtest.connect()

    # Initialize HistoricalDataManager by only passing the broker_client instance
    hdm = HistoricalDataManager(broker_client=broker_for_backtest)

    # Configure ExampleMovingAverageCrossStrategy
    strategy_config_backtest = {
        "symbol": test_symbol,
        "short_window": 5,
        "long_window": 10,
        "quantity": 10,
        "timeframe": data_timeframe_backtest.value # Pass the value of the enum
    }
    strategy_backtest = ExampleMovingAverageCrossStrategy(
        strategy_id="MA_Cross_Test", broker=broker_for_backtest, config=strategy_config_backtest
    )

    # Initialize BacktesterEngine
    engine = BacktesterEngine(
        strategy=strategy_backtest,
        broker=broker_for_backtest,
        historical_data_manager=hdm,
        symbols=[test_symbol],
        timeframe=data_timeframe_backtest.value,
        start_date=start_date_backtest,
        end_date=end_date_backtest,
        generate_analytics_report=True # Ensure report generation is enabled
    )

    logger.info("Starting backtest engine...")
    equity_curve, portfolio_history = engine.run()
    logger.info("Backtest engine finished.")

    if equity_curve:
        logger.info(f"Final Portfolio Value: {equity_curve[-1]:.2f}")
    else:
        logger.info(f"Final Portfolio Value (no trades or activity): {initial_cash_backtest:.2f}")

    logger.info("Trade Log:")
    trade_log = broker_for_backtest.get_trade_history()
    if trade_log:
        for trade in trade_log:
            # Access Trade object attributes directly
            trade_info = (
                f"TradeID: {trade.trade_id}, OrderID: {trade.order_id}, Symbol: {trade.symbol}, "
                f"Side: {trade.side.value}, Qty: {trade.quantity}, Price: {trade.price:.2f}, "
                f"Comm: {trade.commission:.2f}, PnL: {trade.pnl:.2f}, TS: {trade.timestamp}"
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

    # Print path to generated QuantStats report
    report_path = os.path.join(os.getcwd(), "quantstats_report.html")
    logger.info(f"QuantStats report generated at: {report_path}")
    print(f"\nQuantStats report generated at: {report_path}")

    broker_for_backtest.disconnect()
    print("\n" + "=" * 50)
    print("End-to-End Backtesting Workflow with Analytics Finished")
    print("=" * 50 + "\n")

    # Run Strategy Lab Demo
    run_strategy_lab_demo()


import pandas as pd
import logging
from typing import TYPE_CHECKING, Generator, Union, Dict, Iterator

from src.core.models import Candle, Order, Timeframe # Added Timeframe for Candle

if TYPE_CHECKING:
    from src.strategies.base_strategy import BaseStrategy
    from src.broker_api.base_broker_client import BaseBrokerClient # Corrected import path
    from src.broker_api.mock_fyers_client import MockFyersClient

class DataFeedSimulator:
    def __init__(self, historical_data: pd.DataFrame, mock_broker: 'MockFyersClient', default_symbol: str = "DEFAULT_SYMBOL", default_timeframe: Timeframe = Timeframe.MINUTE_1):
        """
        Initializes the DataFeedSimulator.

        :param historical_data: DataFrame with historical market data. 
                                Expected columns: 'timestamp', 'open', 'high', 'low', 'close', 'volume'.
                                Can optionally include 'symbol' and 'timeframe'.
        :param mock_broker: Instance of MockFyersClient.
        :param default_symbol: Symbol to use if 'symbol' column is not in historical_data.
        :param default_timeframe: Timeframe to use if 'timeframe' column is not in historical_data or not a Timeframe enum.
        """
        self.historical_data = historical_data
        self.mock_broker = mock_broker
        self.default_symbol = default_symbol
        self.default_timeframe = default_timeframe
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers: # Ensure logger is configured
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


    def generate_events(self) -> Generator[Union[Candle, Order], None, None]:
        """
        Generates market data events and order update events from historical data.
        """
        if not isinstance(self.historical_data, pd.DataFrame):
            self.logger.error("Historical data is not a pandas DataFrame.")
            return

        for index, row in self.historical_data.iterrows():
            try:
                event_symbol = row.get('symbol', self.default_symbol)
                
                # Handle timeframe: use column if present and valid, else default
                timeframe_value = row.get('timeframe', self.default_timeframe)
                if not isinstance(timeframe_value, Timeframe):
                    # Attempt to convert if it's a string that matches a Timeframe member, e.g. "1minute"
                    try:
                        timeframe_value = Timeframe(timeframe_value)
                    except ValueError:
                        self.logger.warning(f"Invalid timeframe value '{timeframe_value}' in data, using default {self.default_timeframe.value}. Row: {row.to_dict()}")
                        timeframe_value = self.default_timeframe


                market_data_event = Candle(
                    timestamp=pd.to_datetime(row['timestamp']), # Ensure timestamp is datetime
                    symbol=event_symbol,
                    timeframe=timeframe_value, # Add timeframe
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['volume'])
                )
                
                self.logger.debug(f"Yielding Market Data Event: {market_data_event}")
                yield market_data_event

                # Update broker with current bar and process orders
                self.mock_broker.set_current_bar(event_symbol, market_data_event)
                self.mock_broker.current_time = market_data_event.timestamp
                self.mock_broker._process_pending_orders()
                
                order_updates = self.mock_broker.get_simulated_order_updates()
                if order_updates:
                    for order_update in order_updates:
                        self.logger.debug(f"Yielding Order Update Event: {order_update}")
                        yield order_update
            
            except KeyError as e:
                self.logger.error(f"Missing expected column in historical_data: {e}. Row data: {row.to_dict()}")
                continue 
            except Exception as e:
                self.logger.error(f"Error processing row or generating event: {e}. Row data: {row.to_dict()}", exc_info=True)
                continue


class EventHandler:
    def __init__(self, 
                 strategy: 'BaseStrategy', 
                 broker_client: 'BaseBrokerClient', 
                 data_feed_simulator: 'DataFeedSimulator'):
        """
        Initializes the EventHandler.

        :param strategy: The trading strategy instance.
        :param broker_client: The broker client instance.
        :param data_feed_simulator: The data feed simulator instance.
        """
        self.strategy = strategy
        self.broker_client = broker_client # Although stored, it's not directly used in on_bar per latest strategy signature
        self.data_feed_simulator = data_feed_simulator
        
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers: # Ensure logger is configured
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


    def run_simulation_loop(self):
        """
        Runs the simulation loop, processing events from the DataFeedSimulator.
        """
        self.logger.info("Starting simulation loop...")
        
        event_count = 0
        market_event_count = 0
        order_event_count = 0

        for event in self.data_feed_simulator.generate_events():
            event_count += 1
            self.logger.debug(f"Received event #{event_count}: {type(event)} - {event}")
            
            try:
                if isinstance(event, Candle):
                    market_event_count +=1
                    self.logger.info(f"Processing Market Event (Candle) for {event.symbol} at {event.timestamp}")
                    # The on_bar method in BaseStrategy expects: current_bars: Dict[str, 'Candle']
                    # The broker_client is not passed to on_bar directly as per BaseStrategy.on_bar signature.
                    # The strategy accesses the broker via self.broker.
                    self.strategy.on_bar({event.symbol: event}) 
                
                elif isinstance(event, Order):
                    order_event_count +=1
                    self.logger.info(f"Processing Order Update Event: ID {getattr(event, 'id', 'N/A')}, Status {getattr(event, 'status', 'N/A')}")
                    self.strategy.on_order_update(event)
                
                else:
                    self.logger.warning(f"Received unknown event type: {type(event)}")

            except Exception as e:
                # Log exc_info=True to get the full traceback
                self.logger.error(f"Error processing event: {event}. Error: {e}", exc_info=True)
        
        self.logger.info(f"Simulation loop finished. Processed {event_count} total events.")
        self.logger.info(f"Market Events: {market_event_count}, Order Events: {order_event_count}.")

# Example Usage (for testing purposes, can be removed or commented out for production)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_logger = logging.getLogger(__name__)
    main_logger.info("Running event_handler.py example...")

    from src.strategies.base_strategy import BaseStrategy
    from src.broker_api.mock_fyers_client import MockFyersClient
    from src.core.models import OrderType, OrderSide # Removed unused Trade import for main
    from datetime import datetime, timedelta # Ensure datetime is imported for timedelta
    import uuid

    class MockStrategy(BaseStrategy):
        def __init__(self, strategy_id, broker, config=None):
            super().__init__(strategy_id, broker, config)
            self.bars_processed = 0

        def on_bar(self, current_bars: Dict[str, Candle]): # Corrected type hint for Candle
            self.logger.info(f"MockStrategy.on_bar received: Symbols {list(current_bars.keys())}")
            self.bars_processed += 1
            for symbol, candle in current_bars.items():
                if self.bars_processed == 1: # Place order only on the first bar for this symbol
                    self.logger.info(f"MockStrategy: Attempting to place a LIMIT BUY order for {symbol} at price {candle.close * 0.98}")
                    limit_order = Order(
                        id=str(uuid.uuid4()), # Generate a unique ID
                        symbol=symbol,
                        quantity=1,
                        side=OrderSide.BUY,
                        order_type=OrderType.LIMIT,
                        price=round(candle.close * 0.98, 2), # Rounded price
                    )
                    order_id, status = self.broker.place_order(limit_order)
                    self.logger.info(f"MockStrategy: Placed LIMIT order {order_id} for {symbol} with status {status}")
                elif self.bars_processed == 2 and symbol == "TEST_MSFT": # Example: Place another order for a different symbol
                    self.logger.info(f"MockStrategy: Attempting to place a MARKET SELL order for {symbol}")
                    market_order = Order(id=str(uuid.uuid4()), symbol=symbol, quantity=2, side=OrderSide.SELL, order_type=OrderType.MARKET)
                    order_id, status = self.broker.place_order(market_order)
                    self.logger.info(f"MockStrategy: Placed MARKET order {order_id} for {symbol} with status {status}")


        def on_order_update(self, order_update: Order): # Corrected type hint for Order
            self.logger.info(f"MockStrategy.on_order_update received: ID {getattr(order_update, 'id', 'N/A')}, Symbol {getattr(order_update, 'symbol', 'N/A')}, Status {getattr(order_update, 'status', 'N/A')}, Price {getattr(order_update, 'price', 'N/A')}, Executed Price {getattr(order_update, 'executed_price', 'N/A')}")

        def on_fill(self, trade_event): # trade_event is 'Trade' (Trade model not imported here for main example)
            self.logger.info(f"MockStrategy.on_fill received: {trade_event}")

    # Sample historical data for two symbols
    now = datetime.now()
    sample_data_list = []
    for i in range(3): # 3 bars for each symbol
        dt = now - timedelta(minutes=(2-i))
        sample_data_list.append({
            'timestamp': dt, 'symbol': 'TEST_AAPL', 'timeframe': Timeframe.MINUTE_1.value, # Use enum value
            'open': 150.0 + i*0.5, 'high': 151.0 + i*0.5, 'low': 149.5 + i*0.5, 
            'close': 150.5 + i*0.5, 'volume': 1000 + i*100
        })
        sample_data_list.append({
            'timestamp': dt, 'symbol': 'TEST_MSFT', 'timeframe': "1minute", # Test string conversion
            'open': 250.0 + i*0.5, 'high': 251.0 + i*0.5, 'low': 249.5 + i*0.5, 
            'close': 250.5 + i*0.5, 'volume': 800 + i*100
        })
    
    historical_df = pd.DataFrame(sample_data_list)
    # Sort by timestamp to ensure chronological processing if mixing symbols like this
    historical_df.sort_values(by='timestamp', inplace=True)
    
    mock_broker_instance = MockFyersClient(historical_data={
        'TEST_AAPL': [], 'TEST_MSFT': [] # Empty lists for get_historical_candles if strategy uses it
    })
    # Initialize broker time to be before or at the first data point.
    if not historical_df.empty:
        mock_broker_instance.current_time = historical_df['timestamp'].iloc[0] - timedelta(seconds=1)


    mock_strategy_instance = MockStrategy(strategy_id="test_event_handler_strat", broker=mock_broker_instance)

    # For DataFeedSimulator, symbol in historical_data takes precedence. default_symbol is a fallback.
    data_feed_sim = DataFeedSimulator(historical_data=historical_df, 
                                      mock_broker=mock_broker_instance,
                                      default_symbol="FALLBACK_SYM",
                                      default_timeframe=Timeframe.MINUTE_1) # Corrected to use the enum member directly
                                      
    event_handler = EventHandler(strategy=mock_strategy_instance, 
                                 broker_client=mock_broker_instance, 
                                 data_feed_simulator=data_feed_sim)
    
    main_logger.info("Running simulation loop with example data...")
    event_handler.run_simulation_loop()
    main_logger.info("Example simulation finished.")
    main_logger.info(f"Strategy processed {mock_strategy_instance.bars_processed} total on_bar calls (may be more than unique bars if multiple symbols).")

    main_logger.info("\n--- Broker State Post-Simulation ---")
    main_logger.info(f"Cash: {mock_broker_instance.cash}")
    main_logger.info("Positions:")
    for sym, pos_data in mock_broker_instance.positions.items():
        main_logger.info(f"  {sym}: Qty={pos_data['quantity']}, AvgPrice={pos_data['average_price']:.2f}, LastPrice={pos_data['last_price']:.2f}")
    
    main_logger.info("\nAll Orders Logged by Broker:")
    for order_obj in mock_broker_instance.all_orders:
        attrs = {
            attr: getattr(order_obj, attr, 'N/A') 
            for attr in ['id', 'symbol', 'status', 'order_type', 'side', 'quantity', 'price', 'trigger_price', 'executed_price', 'commission', 'reject_reason', 'timestamp', 'filled_timestamp', 'cancelled_timestamp']
        }
        main_logger.info(f"  Order: {attrs}")

    main_logger.info("\nTrade Log:")
    for trade in mock_broker_instance.trade_log: # Assuming Trade is a dict here
        main_logger.info(f"  Trade: {trade}")

    # Check if any updates were left in the broker's log (should be empty if processed correctly)
    remaining_updates = mock_broker_instance.get_simulated_order_updates()
    main_logger.info(f"\nSimulated order updates log in broker (should be empty): {remaining_updates}")
    if not remaining_updates:
        main_logger.info("Broker's simulated order update log is correctly empty.")
    else:
        main_logger.warning("Broker's simulated order update log is NOT empty. Some updates were not processed.")

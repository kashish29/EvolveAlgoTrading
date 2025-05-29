import logging
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Any, Optional
import uuid

from src.core.models import Signal, Order, OrderSide
from src.core.enums import OrderType, OrderStatus

if TYPE_CHECKING:
    from src.broker_api.base_broker_client import BaseBrokerClient

class ExecutionHandler:
    def __init__(self, broker_client: 'BaseBrokerClient'):
        """
        Initializes the ExecutionHandler.

        :param broker_client: An instance of a class that implements BaseBrokerClient.
        """
        self.broker_client = broker_client
        self.logger = logging.getLogger(self.__class__.__name__)
        # Basic logging setup if not configured globally
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"ExecutionHandler initialized with broker client: {self.broker_client.__class__.__name__}")

    def execute_signal(self, signal: Signal):
        """
        Converts a Signal object into an Order object and places it using the broker client.

        :param signal: The Signal object containing trade information.
        """
        logging.info(f"Executing signal: {signal}")
        order_id = None # Initialize order_id
        try:
            logging.info(f"Signal details: {signal.symbol}, {signal.side}, {signal.quantity}")
            # --- Convert Signal to Order ---
            # Map signal.side (which is already OrderSide type based on current Signal model) to order.side
            order_side = signal.side 
            if not isinstance(order_side, OrderSide):
                # This check is more for robustness if Signal model changes.
                # Assuming signal.side is already validated or an enum.
                try:
                    order_side = OrderSide(str(signal.side).upper())
                except ValueError:
                    self.logger.error(f"Invalid signal side '{signal.side}' for signal ID {getattr(signal, 'id', 'N/A')}. Cannot determine OrderSide.")
                    return


            # Map signal.order_type (already OrderType) to order.order_type
            order_type = signal.order_type
            if not isinstance(order_type, OrderType):
                 # This check is for robustness if Signal model changes.
                try:
                    order_type = OrderType(str(signal.order_type).upper())
                except ValueError:
                    self.logger.error(f"Invalid order_type '{signal.order_type}' in signal ID {getattr(signal, 'id', 'N/A')}. Cannot create order.")
                    return

            order_params = {
                "id": None, # Explicitly set id to None, as it's assigned by broker
                "symbol": signal.symbol,
                "quantity": signal.quantity,
                "side": order_side,
                "order_type": order_type,
                "timestamp": datetime.now(),
                "status": OrderStatus.PENDING, # Initial status before broker confirmation
            }
            self.logger.debug(f"Initial order_params before price/trigger_price assignment: {order_params}")

            if order_type == OrderType.LIMIT or order_type == OrderType.STOP_LIMIT:
                if signal.price is None:
                    self.logger.error(f"{order_type.value} order signal ID {getattr(signal, 'id', 'N/A')} for {signal.symbol} is missing 'price'.")
                    return
                order_params["price"] = signal.price
                self.logger.debug(f"Assigned price {signal.price} for {order_type.value} order.")
            
            if order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT, OrderType.STOP]:
                if signal.stop_price is None: # stop_price from Signal maps to trigger_price in Order
                    self.logger.error(f"{order_type.value} order signal ID {getattr(signal, 'id', 'N/A')} for {signal.symbol} is missing 'stop_price' (for trigger_price).")
                    return
                order_params["trigger_price"] = signal.stop_price
                self.logger.debug(f"Assigned trigger_price {signal.stop_price} for {order_type.value} order.")

            # Include other details from signal if they are relevant for Order
            # Example: signal.timeframe could be order.timeframe if Order model has it
            # Construct Order directly from signal attributes, ensuring correct mapping
            order_to_place = Order(
                id=str(uuid.uuid4()), # Generate a unique ID for the order
                symbol=signal.symbol,
                quantity=int(signal.quantity) if signal.quantity is not None else 0,
                side=signal.side,
                order_type=signal.order_type,
                price=signal.price,
                trigger_price=signal.stop_price, # Map signal.stop_price to order.trigger_price
                # status and timestamp will be set by default in Order dataclass or by broker
            )
            self.logger.info(f"Constructed Order: {order_to_place} from Signal ID {getattr(signal, 'id', 'N/A')}")
            self.logger.debug(f"Order status before placing with broker: {order_to_place.status}")
 
             # --- Place the Order ---
            self.logger.info(f"Placing order for {order_to_place.symbol} with broker...")
            
            order_id, broker_status_str = self.broker_client.place_order(order_to_place)
            
            self.logger.info(
                 f"Order placement attempt for {order_to_place.symbol} (Signal ID {getattr(signal, 'id', 'N/A')}) "
                 f"resulted in: Broker Order ID: {order_id}, Status from broker: {broker_status_str}."
            )
            
             # Update the order object with the broker-assigned ID and status
             # This is useful if the order object is used further (e.g., stored, passed to strategy)
            if order_id: # If an ID was returned
                 self.logger.info(f"Order ID received from broker: {order_id}")
                 setattr(order_to_place, 'id', order_id)
            else:
                 self.logger.warning("No Order ID received from broker.")
            try:
                 # Attempt to map broker status string to OrderStatus enum
                 new_status = OrderStatus(broker_status_str.upper())
                 setattr(order_to_place, 'status', new_status)
                 self.logger.debug(f"Order status updated to: {order_to_place.status} after broker response.")
            except ValueError:
                 self.logger.warning(f"Broker status '{broker_status_str}' for order {order_id} is not a recognized OrderStatus enum member. Storing raw status.")
                 # Optionally store the raw string if OrderStatus enum doesn't cover it
                 # setattr(order_to_place, 'raw_broker_status', broker_status_str)

        except Exception as e:
            self.logger.error(
                f"Failed to execute signal ID {getattr(signal, 'id', 'N/A')} for {signal.symbol}. Error: {e}",
                exc_info=True 
            )

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    from src.broker_api.mock_fyers_client import MockFyersClient
    from src.core.models import Candle, Timeframe # For setting up mock broker
    
    mock_broker = MockFyersClient(initial_cash=100000)
    mock_broker.connect() 
    
    exec_handler = ExecutionHandler(broker_client=mock_broker)

    # Setup current bar for market order simulation in MockFyersClient
    now = datetime.now()
    current_test_bar = Candle(
        symbol="TESTSYM", timestamp=now, timeframe=Timeframe.MINUTE_1,
        open=100, high=102, low=99, close=101, volume=1000
    )
    mock_broker.set_current_bar("TESTSYM", current_test_bar)
    mock_broker.current_time = now # Assign datetime object directly

    # Scenario 1: Market Buy Order (Signal.side is OrderSide.BUY)
    print("\n--- Scenario 1: Market Buy Order ---")
    market_buy_signal = Signal(
        timestamp=now, # Added missing timestamp
        symbol="TESTSYM", side=OrderSide.BUY, quantity=10,
        order_type=OrderType.MARKET, comment="Test market buy"
    )
    exec_handler.execute_signal(market_buy_signal)
    # Expected: Order placed, position updated in mock_broker.

    # Scenario 2: Limit Sell Order
    print("\n--- Scenario 2: Limit Sell Order ---")
    limit_sell_signal = Signal(
        timestamp=now, # Added missing timestamp
        symbol="ANOTHER_SYM", side=OrderSide.SELL, quantity=5,
        order_type=OrderType.LIMIT, price=205.50, comment="Test limit sell"
    )
    exec_handler.execute_signal(limit_sell_signal)
    # Expected: Order placed, visible in mock_broker.open_orders.

    # Scenario 3: Stop-Market Buy Order
    print("\n--- Scenario 3: Stop-Market Buy Order ---")
    # Need to set current bar for 'STOPSYM' if mock broker uses it for validation/processing
    mock_broker.set_current_bar("STOPSYM", Candle(symbol="STOPSYM", timestamp=now, timeframe=Timeframe.MINUTE_1, open=90, high=92, low=89, close=91, volume=500))
    mock_broker.current_time = now # Assign datetime object directly
    stop_market_buy_signal = Signal(
        timestamp=now, # Added missing timestamp
        symbol="STOPSYM", side=OrderSide.BUY, quantity=3,
        order_type=OrderType.STOP_MARKET, stop_price=93.00, # stop_price from Signal -> trigger_price for Order
        comment="Test stop-market buy"
    )
    exec_handler.execute_signal(stop_market_buy_signal)
    # Expected: Order placed, visible in mock_broker.open_orders.

    # Scenario 4: Stop-Limit Sell Order
    print("\n--- Scenario 4: Stop-Limit Sell Order ---")
    mock_broker.set_current_bar("SLSYM", Candle(symbol="SLSYM", timestamp=now, timeframe=Timeframe.MINUTE_1, open=110, high=112, low=109, close=111, volume=600))
    mock_broker.current_time = now # Assign datetime object directly
    stop_limit_sell_signal = Signal(
        timestamp=now, # Added missing timestamp
        symbol="SLSYM", side=OrderSide.SELL, quantity=8,
        order_type=OrderType.STOP_LIMIT, price=108.00, stop_price=108.50,
        comment="Test stop-limit sell"
    )
    exec_handler.execute_signal(stop_limit_sell_signal)
    # Expected: Order placed, visible in mock_broker.open_orders.

    # Scenario 5: Invalid Signal (e.g., missing price for LIMIT order)
    print("\n--- Scenario 5: Invalid Limit Order (missing price) ---")
    invalid_limit_signal = Signal(
        timestamp=now, # Added missing timestamp
        symbol="BADSYM_LIMIT", side=OrderSide.BUY, quantity=1,
        order_type=OrderType.LIMIT # Price is missing
    )
    exec_handler.execute_signal(invalid_limit_signal)
    # Expected: Error logged, order not placed.

    # Scenario 6: Invalid Signal (missing stop_price for STOP_MARKET order)
    # This scenario is implicitly handled by the broker's place_order validation.
    # No direct change to Signal constructor needed here.
    print("\n--- Scenario 6: Invalid Stop-Market Order (missing stop_price) ---")
    invalid_stop_signal = Signal(
        # id="sig_invalid_stop_006", # Removed unexpected keyword argument 'id'
        timestamp=now, # Added missing timestamp
        symbol="BADSYM_STOP", side=OrderSide.SELL, quantity=2,
        order_type=OrderType.STOP_MARKET # stop_price is missing
    )
    exec_handler.execute_signal(invalid_stop_signal)
    # Expected: Error logged, order not placed.

    # Display final state of mock broker for verification
    print("\n--- Broker State After All Test Scenarios ---")
    print(f"Cash: {mock_broker.get_balance()['cash']}")
    print("Positions:")
    for pos in mock_broker.get_positions(): print(f"  {pos}")
    print("Open Orders:")
    for order_id, order_obj in mock_broker.open_orders.items(): print(f"  ID: {order_id}, Order: {order_obj}")
    print("All Orders Log:")
    for i, order_obj in enumerate(mock_broker.all_orders): print(f"  {i+1}. {order_obj}")

    mock_broker.disconnect()
    print("\nExecutionHandler example scenarios completed.")
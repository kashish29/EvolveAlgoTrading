import logging
from datetime import datetime
from typing import TYPE_CHECKING

from src.core.models import Signal, Order, OrderStatus, OrderSide, OrderType 

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
        self.logger.info(f"Received signal to execute: {signal}")

        try:
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
                "symbol": signal.symbol,
                "quantity": signal.quantity,
                "side": order_side,
                "order_type": order_type,
                "timestamp": datetime.now(), 
                "status": OrderStatus.PENDING_OPEN, # Initial status before broker confirmation
                # id will be None; broker assigns it.
            }

            if order_type == OrderType.LIMIT or order_type == OrderType.STOP_LIMIT:
                if signal.price is None:
                    self.logger.error(f"{order_type.value} order signal ID {getattr(signal, 'id', 'N/A')} for {signal.symbol} is missing 'price'.")
                    return
                order_params["price"] = signal.price
            
            if order_type == OrderType.STOP_MARKET or order_type == OrderType.STOP_LIMIT:
                if signal.stop_price is None: # stop_price from Signal maps to trigger_price in Order
                    self.logger.error(f"{order_type.value} order signal ID {getattr(signal, 'id', 'N/A')} for {signal.symbol} is missing 'stop_price' (for trigger_price).")
                    return
                order_params["trigger_price"] = signal.stop_price

            # Include other details from signal if they are relevant for Order
            # Example: signal.timeframe could be order.timeframe if Order model has it
            if hasattr(signal, 'timeframe') and signal.timeframe is not None:
                order_params['timeframe'] = signal.timeframe
            
            # If signal.details contains relevant Order fields, they could be mapped here.
            # For now, assuming core fields are directly on Signal object or handled above.
            # If signal.details is used: order_params.update(signal.details) - with caution.


            order_to_place = Order(**order_params)
            self.logger.info(f"Constructed Order: {order_to_place} from Signal ID {getattr(signal, 'id', 'N/A')}")

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
                setattr(order_to_place, 'id', order_id)
            try:
                # Attempt to map broker status string to OrderStatus enum
                setattr(order_to_place, 'status', OrderStatus(broker_status_str.upper()))
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
    logging.basicConfig(level=logging.DEBUG)
    
    from src.broker_api.mock_fyers_client import MockFyersClient 
    from src.core.models import Candle, Timeframe # For setting up mock broker
    
    mock_broker = MockFyersClient(initial_cash=100000)
    mock_broker.connect() 
    
    exec_handler = ExecutionHandler(broker_client=mock_broker)

    # Setup current bar for market order simulation in MockFyersClient
    now = datetime.now()
    current_test_bar = Candle(
        symbol="TESTSYM", timestamp=now, timeframe=Timeframe.ONE_MINUTE,
        open=100, high=102, low=99, close=101, volume=1000
    )
    mock_broker.set_current_bar("TESTSYM", current_test_bar)
    mock_broker.current_time = now

    # Scenario 1: Market Buy Order (Signal.side is OrderSide.BUY)
    print("\n--- Scenario 1: Market Buy Order ---")
    market_buy_signal = Signal(
        id="sig_market_buy_001", symbol="TESTSYM", side=OrderSide.BUY, quantity=10,
        order_type=OrderType.MARKET, details={"info": "Test market buy"}
    )
    exec_handler.execute_signal(market_buy_signal)
    # Expected: Order placed, position updated in mock_broker.

    # Scenario 2: Limit Sell Order
    print("\n--- Scenario 2: Limit Sell Order ---")
    limit_sell_signal = Signal(
        id="sig_limit_sell_002", symbol="ANOTHER_SYM", side=OrderSide.SELL, quantity=5,
        order_type=OrderType.LIMIT, price=205.50, details={"info": "Test limit sell"}
    )
    exec_handler.execute_signal(limit_sell_signal)
    # Expected: Order placed, visible in mock_broker.open_orders.

    # Scenario 3: Stop-Market Buy Order
    print("\n--- Scenario 3: Stop-Market Buy Order ---")
    # Need to set current bar for 'STOPSYM' if mock broker uses it for validation/processing
    mock_broker.set_current_bar("STOPSYM", Candle(symbol="STOPSYM", timestamp=now, timeframe=Timeframe.ONE_MINUTE, open=90, high=92, low=89, close=91, volume=500))
    mock_broker.current_time = now
    stop_market_buy_signal = Signal(
        id="sig_stop_market_003", symbol="STOPSYM", side=OrderSide.BUY, quantity=3,
        order_type=OrderType.STOP_MARKET, stop_price=93.00, # stop_price from Signal -> trigger_price for Order
        details={"info": "Test stop-market buy"}
    )
    exec_handler.execute_signal(stop_market_buy_signal)
    # Expected: Order placed, visible in mock_broker.open_orders.

    # Scenario 4: Stop-Limit Sell Order
    print("\n--- Scenario 4: Stop-Limit Sell Order ---")
    mock_broker.set_current_bar("SLSYM", Candle(symbol="SLSYM", timestamp=now, timeframe=Timeframe.ONE_MINUTE, open=110, high=112, low=109, close=111, volume=600))
    mock_broker.current_time = now
    stop_limit_sell_signal = Signal(
        id="sig_stop_limit_004", symbol="SLSYM", side=OrderSide.SELL, quantity=8,
        order_type=OrderType.STOP_LIMIT, price=108.00, stop_price=108.50,
        details={"info": "Test stop-limit sell"}
    )
    exec_handler.execute_signal(stop_limit_sell_signal)
    # Expected: Order placed, visible in mock_broker.open_orders.

    # Scenario 5: Invalid Signal (e.g., missing price for LIMIT order)
    print("\n--- Scenario 5: Invalid Limit Order (missing price) ---")
    invalid_limit_signal = Signal(
        id="sig_invalid_limit_005", symbol="BADSYM_LIMIT", side=OrderSide.BUY, quantity=1,
        order_type=OrderType.LIMIT # Price is missing
    )
    exec_handler.execute_signal(invalid_limit_signal)
    # Expected: Error logged, order not placed.

    # Scenario 6: Invalid Signal (missing stop_price for STOP_MARKET order)
    print("\n--- Scenario 6: Invalid Stop-Market Order (missing stop_price) ---")
    invalid_stop_signal = Signal(
        id="sig_invalid_stop_006", symbol="BADSYM_STOP", side=OrderSide.SELL, quantity=2,
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

# Ensure a trailing newline
```

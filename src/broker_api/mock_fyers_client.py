import random
import logging
from datetime import datetime
from src.broker_api.base_broker_client import BaseBrokerClient
# Forward references for type hinting if needed, though Order and Timeframe are not used directly here yet
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from src.core.models import Order, Timeframe 
from typing import Union, Dict, Any # For type hinting historical_data

class MockFyersClient(BaseBrokerClient):
    def __init__(self, 
                 historical_data: Union[Dict, Any] = None, # Can be HDM instance or dict
                 initial_cash: float = 100000.0, 
                 commission_rate: float = 0.0003):
        self.current_time = None
        self.initial_cash = initial_cash
        self.cash: float = initial_cash
        self.positions: dict = {}  # Stores symbol: {'quantity': int, 'average_price': float}
        self.open_orders: dict = {} # Stores order_id: Order
        self.all_orders: list = []    # Stores all Order objects, including historical
        self.trade_log: list = []     # Stores Trade objects or dicts representing trades
        self.order_id_counter: int = 0
        self.trade_id_counter: int = 0
        
        # historical_data can be an instance of HistoricalDataManager or a dict
        self.historical_data = historical_data if historical_data is not None else {}
        
        self.current_bars: dict = {} # Stores symbol: Candle for the current bar
        self.commission_rate: float = commission_rate
        # Simple slippage model: price +/- up to 0.05%
        self.slippage_model = lambda price: price * (1 + random.uniform(-0.0005, 0.0005)) # Corrected slippage
        
        self.logger = logging.getLogger(self.__class__.__name__) # Use class name for logger
        # Basic config for logging, consider moving to a global config if app expands
        # or if not already configured by a higher-level module (like main.py)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger.info(f"MockFyersClient initialized with initial_cash: {initial_cash}, commission_rate: {commission_rate}.")

    def connect(self):
        print("MockFyersClient connected.")
        self.logger.info("MockFyersClient connected.")

    def disconnect(self):
        print("MockFyersClient disconnected.")
        self.logger.info("MockFyersClient disconnected.")

    def get_balance(self) -> dict:
        # Simulate margin for now
        return {"cash": self.cash, "margin_available": self.cash, "margin_used": 0.0}

    def get_positions(self) -> list: # Should eventually be list['Position']
        # Returns a list of position objects/dictionaries
        # self.positions stores symbol: {'quantity': int, 'average_price': float, 'symbol': str, ...}
        return list(self.positions.values())

    def get_order_book(self, symbol: str) -> dict:
        # Return a simplified hardcoded order book
        # These prices can be made more dynamic later if needed
        return {
            "symbol": symbol,
            "best_bid": {"price": 100.00, "quantity": 10},
            "best_ask": {"price": 100.05, "quantity": 10}
        }

    def get_order_history(self, order_id: str = None, status: str = None) -> list['Order']:
        filtered_orders = self.all_orders
        if order_id is not None:
            # Assuming Order objects will have an 'id' attribute
            filtered_orders = [order for order in filtered_orders if getattr(order, 'id', None) == order_id]
        
        if status is not None:
            # Assuming Order objects will have a 'status' attribute
            filtered_orders = [order for order in filtered_orders if getattr(order, 'status', None) == status.upper()] # Assuming status might be compared case-insensitively or stored in upper
        
        return filtered_orders

    def get_trade_history(self, order_id: str = None) -> list['Trade']:
        filtered_trades = self.trade_log
        if order_id is not None:
            # Assuming Trade objects will have an 'order_id' attribute
            filtered_trades = [trade for trade in filtered_trades if getattr(trade, 'order_id', None) == order_id]
        
        return filtered_trades

    def place_order(self, order: 'Order') -> tuple[str, str]:
        self.order_id_counter += 1
        order_id = f"mock_order_{self.order_id_counter}"
        setattr(order, 'id', order_id) # Set the order ID on the order object

        # Correctly access Enum .value for string representation
        order_type_attr = getattr(order, 'order_type', None)
        order_type_str = order_type_attr.value if hasattr(order_type_attr, 'value') else str(order_type_attr)
        order_type_processed = order_type_str.upper()

        order_symbol = getattr(order, 'symbol', None)
        order_quantity = getattr(order, 'quantity', 0)
        
        order_side_attr = getattr(order, 'side', None)
        order_side_str = order_side_attr.value if hasattr(order_side_attr, 'value') else str(order_side_attr)
        order_side_processed = order_side_str.upper()


        if not all([order_symbol, order_quantity > 0, order_side_processed in ["BUY", "SELL"], order_type_processed]):
            self.logger.error(f"Order validation failed: {order_symbol}, {order_quantity}, {order_side_processed}, {order_type_processed}")
            setattr(order, 'status', "REJECTED")
            setattr(order, 'reject_reason', "Invalid order parameters")
            self.all_orders.append(order) # Log rejected order
            return order_id, "REJECTED"

        # Use processed string versions for logic
        if order_type_processed == "MARKET":
            # MARKET order logic
            base_price = None
            # Attempt to get price from historical_data if it's a dict (e.g. for pre-set last_price)
            if isinstance(self.historical_data, dict):
                symbol_data_in_historical = self.historical_data.get(order_symbol)
                if symbol_data_in_historical and 'last_price' in symbol_data_in_historical:
                    base_price = symbol_data_in_historical['last_price']
            
            # If not found in historical_data dict, or historical_data is not a dict (e.g. HDM instance),
            # try to use the current bar's close price. This is the primary source during backtesting.
            if base_price is None:
                current_bar_data = self.get_current_bar(order_symbol)
                if current_bar_data and hasattr(current_bar_data, 'close'):
                    base_price = current_bar_data.close
                else:
                    # Absolute fallback if no other price source is available
                    base_price = 100.00  # Default fallback price
                    self.logger.warning(
                        f"Market order {order_id} for {order_symbol}: "
                        f"last_price not in historical_data dict and no current bar available. "
                        f"Using default base_price: {base_price}."
                    )
            
            fill_price = self.slippage_model(base_price)
            trade_value = fill_price * order_quantity
            commission = trade_value * self.commission_rate

            # Increment Trade ID & Create Trade Object
            self.trade_id_counter += 1
            trade = {
                "trade_id": f"mock_trade_{self.trade_id_counter}",
                "order_id": order_id,
                "symbol": order_symbol,
                "quantity": order_quantity,
                "price": fill_price,
                "side": order_side_processed, # Use processed string value
                "timestamp": self.current_time, # Assumes self.current_time is set
                "commission": commission
            }
            self.trade_log.append(trade)

            # Update Cash
            if order_side_processed == "BUY":
                self.cash -= (trade_value + commission)
            elif order_side_processed == "SELL":
                self.cash += (trade_value - commission)

            # Update Positions
            if order_symbol not in self.positions:
                self.positions[order_symbol] = {
                    "symbol": order_symbol, 
                    "quantity": 0, 
                    "average_price": 0.0,
                    "pnl": 0.0, # PnL calculation would be more complex
                    "last_price": fill_price 
                }
            
            current_pos = self.positions[order_symbol]
            if order_side_processed == "BUY":
                new_total_value = (current_pos['average_price'] * current_pos['quantity']) + (fill_price * order_quantity)
                current_pos['quantity'] += order_quantity
                current_pos['average_price'] = new_total_value / current_pos['quantity'] if current_pos['quantity'] != 0 else fill_price
            elif order_side_processed == "SELL":
                # Simple assumption: selling reduces existing long or initiates/increases short.
                # P&L on sell is realized if closing a long. Average price for shorts is more complex.
                # For now, just adjust quantity. If quantity becomes 0, avg_price is reset.
                current_pos['quantity'] -= order_quantity
                if current_pos['quantity'] == 0:
                    current_pos['average_price'] = 0.0
                # If current_pos['quantity'] < 0, it's a short position. 
                # Avg price of shorts needs careful handling (e.g. separate tracking or weighted average)
                # For now, if it goes short, average_price might not be meaningful in the same way as for longs.

            current_pos['last_price'] = fill_price

            # Update Order Status
            setattr(order, 'status', "COMPLETED")
            setattr(order, 'filled_timestamp', self.current_time)
            setattr(order, 'executed_price', fill_price)
            setattr(order, 'commission', commission) # Store commission on order too

            self.all_orders.append(order)
            self.logger.info(f"Market order {order_id} for {order_quantity} {order_symbol} @ {fill_price:.2f} COMPLETED.")
            return order_id, "COMPLETED"
        
        elif order_type_processed in ["LIMIT", "STOP"]: # Use processed string
            required_price_attr = 'price' if order_type_processed == "LIMIT" else 'trigger_price'
            if getattr(order, required_price_attr, None) is None:
                self.logger.error(f"{order_type_processed} order {order_id} for {order_symbol} REJECTED: Missing {required_price_attr}.")
                setattr(order, 'status', "REJECTED")
                setattr(order, 'reject_reason', f"Missing {required_price_attr}")
                self.all_orders.append(order)
                return order_id, "REJECTED"

            setattr(order, 'status', "ACCEPTED") # Or "PENDING"
            setattr(order, 'timestamp', self.current_time) # Acceptance time
            self.open_orders[order_id] = order
            self.all_orders.append(order)
            self.logger.info(f"{order_type_processed} order {order_id} for {order_quantity} {order_symbol} ACCEPTED.")
            return order_id, getattr(order, 'status')
        
        else:
            # Fallback for unknown order types
            self.logger.error(f"Unknown order type {order_type_processed} for order {order_id}. REJECTED.")
            setattr(order, 'status', "REJECTED")
            setattr(order, 'reject_reason', f"Unknown order type: {order_type_processed}")
            self.all_orders.append(order)
            return order_id, "REJECTED"

    def _process_pending_orders(self): # Signature changed, no current_bar argument
        # Iterate over a copy of open_orders.items() to allow modification
        for order_id, order in list(self.open_orders.items()):
            order_symbol = getattr(order, 'symbol') # Should exist if order was accepted
            if not order_symbol:
                self.logger.error(f"Order {order_id} has no symbol, cannot process.")
                continue

            current_bar_for_order_symbol = self.get_current_bar(order_symbol)

            if not current_bar_for_order_symbol:
                # self.logger.warning(f"No current bar data for symbol {order_symbol} to process order {order_id}. Skipping for this timestamp.")
                continue # Skip if no bar data for this order's symbol for the current timestamp

            order_type_attr = getattr(order, 'order_type', None)
            order_type_str = order_type_attr.value if hasattr(order_type_attr, 'value') else str(order_type_attr)
            order_type_processed = order_type_str.upper()
            
            order_side_attr = getattr(order, 'side', None)
            order_side_str = order_side_attr.value if hasattr(order_side_attr, 'value') else str(order_side_attr)
            order_side_processed = order_side_str.upper()

            order_quantity = getattr(order, 'quantity', 0)
            
            # Common attributes for current_bar_for_order_symbol, ensure they exist
            bar_open = getattr(current_bar_for_order_symbol, 'open', None)
            bar_high = getattr(current_bar_for_order_symbol, 'high', None)
            bar_low = getattr(current_bar_for_order_symbol, 'low', None)
            bar_timestamp = getattr(current_bar_for_order_symbol, 'timestamp', self.current_time) # Fallback to current_time if bar has no timestamp

            if None in [bar_open, bar_high, bar_low]:
                self.logger.warning(f"Skipping order {order_id} for symbol {order_symbol} due to incomplete current_bar data: O:{bar_open} H:{bar_high} L:{bar_low}")
                continue

            executed = False
            actual_fill_price = None

            if order_type_processed == "LIMIT": # Use processed string
                order_price = getattr(order, 'price')
                if order_side_processed == "BUY" and bar_low <= order_price: 
                    actual_fill_price = min(bar_open, order_price)
                    executed = True
                elif order_side_processed == "SELL" and bar_high >= order_price: 
                    actual_fill_price = max(bar_open, order_price)
                    executed = True
            
            elif order_type_processed == "STOP": # Use processed string
                trigger_price = getattr(order, 'trigger_price') 
                if order_side_processed == "BUY" and bar_high >= trigger_price:
                    # Stop Buy triggered, execute as market
                    base_fill_price = max(bar_open, trigger_price) 
                    actual_fill_price = self.slippage_model(base_fill_price)
                    executed = True
                    self.logger.info(f"STOP BUY order {order_id} for {order_symbol} triggered at {trigger_price:.2f} (bar high: {bar_high:.2f}). Base fill: {base_fill_price:.2f}, Slippage fill: {actual_fill_price:.2f}")
                elif order_side_processed == "SELL" and bar_low <= trigger_price:
                    # Stop Sell triggered, execute as market
                    base_fill_price = min(bar_open, trigger_price) 
                    actual_fill_price = self.slippage_model(base_fill_price)
                    executed = True
                    self.logger.info(f"STOP SELL order {order_id} for {order_symbol} triggered at {trigger_price:.2f} (bar low: {bar_low:.2f}). Base fill: {base_fill_price:.2f}, Slippage fill: {actual_fill_price:.2f}")

            if executed and actual_fill_price is not None:
                trade_value = actual_fill_price * order_quantity
                commission = trade_value * self.commission_rate

                # Increment Trade ID & Create Trade Object
                self.trade_id_counter += 1
                trade = {
                    "trade_id": f"mock_trade_{self.trade_id_counter}",
                    "order_id": order_id,
                    "symbol": order_symbol,
                    "quantity": order_quantity,
                    "price": actual_fill_price,
                "side": order_side_processed, # Use processed string value
                    "timestamp": bar_timestamp,
                    "commission": commission
                }
                self.trade_log.append(trade)

                # Update Cash
                if order_side_processed == "BUY":
                    self.cash -= (trade_value + commission)
                elif order_side_processed == "SELL":
                    self.cash += (trade_value - commission)

                # Update Positions (reusing logic similar to MARKET orders)
                if order_symbol not in self.positions:
                    self.positions[order_symbol] = {"symbol": order_symbol, "quantity": 0, "average_price": 0.0, "pnl": 0.0, "last_price": actual_fill_price}
                
                current_pos = self.positions[order_symbol]
                if order_side_processed == "BUY":
                    new_total_value = (current_pos['average_price'] * current_pos['quantity']) + (actual_fill_price * order_quantity)
                    current_pos['quantity'] += order_quantity
                    current_pos['average_price'] = new_total_value / current_pos['quantity'] if current_pos['quantity'] != 0 else actual_fill_price
                elif order_side_processed == "SELL":
                    current_pos['quantity'] -= order_quantity
                    if current_pos['quantity'] == 0:
                        current_pos['average_price'] = 0.0
                    # Further P&L/short position avg price logic can be added here if needed
                current_pos['last_price'] = actual_fill_price

                # Update Order Status
                setattr(order, 'status', "COMPLETED")
                setattr(order, 'executed_price', actual_fill_price)
                setattr(order, 'filled_timestamp', bar_timestamp)
                setattr(order, 'commission', commission)
                
                del self.open_orders[order_id]
                self.logger.info(f"{order_type_processed} order {order_id} for {order_quantity} {order_symbol} @ {actual_fill_price:.2f} COMPLETED. Commission: {commission:.2f}")


    def modify_order(self, order_id: str, new_price: float = None, new_quantity: int = None, new_trigger_price: float = None) -> tuple[bool, str]:
        if order_id not in self.open_orders:
            self.logger.warning(f"Attempt to modify order {order_id} which is not in open_orders.")
            return False, "Order not found or not modifiable"

        order = self.open_orders[order_id]
        order_status = getattr(order, 'status', '').upper()

        # Typically, only "ACCEPTED" or "PENDING" (if used) orders can be modified.
        # If it was "MODIFIED" previously, it should still be "ACCEPTED" or "PENDING" effectively.
        if order_status not in ["ACCEPTED", "PENDING"]: # Add any other modifiable statuses here
            self.logger.warning(f"Order {order_id} status {order_status} does not allow modification.")
            return False, f"Order status {order_status} does not allow modification"

        modified_params = []
        if new_price is not None:
            setattr(order, 'price', new_price)
            modified_params.append(f"Price={new_price}")
        
        if new_quantity is not None:
            if new_quantity <= 0:
                self.logger.warning(f"Attempt to modify order {order_id} to invalid quantity {new_quantity}.")
                return False, "Invalid quantity for modification"
            setattr(order, 'quantity', new_quantity)
            modified_params.append(f"Quantity={new_quantity}")

        # Only try to set trigger_price if it's a STOP order (or relevant type)
        # For simplicity, we allow setting it if provided, assuming the order object handles its relevance.
        if new_trigger_price is not None:
            setattr(order, 'trigger_price', new_trigger_price)
            modified_params.append(f"Trigger={new_trigger_price}")
        
        if not modified_params:
            self.logger.info(f"No parameters provided to modify for order {order_id}.")
            return False, "No modification parameters provided"

        setattr(order, 'modified_timestamp', self.current_time)
        # The status remains "ACCEPTED" so it can still be processed by _process_pending_orders
        # If a specific "MODIFIED_ACCEPTED" status was needed, it would be set here.
        # setattr(order, 'status', 'MODIFIED_ACCEPTED') 

        self.logger.info(f"Order {order_id} modified: {', '.join(modified_params)}.")
        return True, "Order modified successfully"

    def cancel_order(self, order_id: str) -> tuple[bool, str]:
        if order_id not in self.open_orders:
            self.logger.warning(f"Attempt to cancel order {order_id} which is not in open_orders.")
            return False, "Order not found in open orders"

        order = self.open_orders[order_id]
        
        # Set status in all_orders list as well
        # The order object in all_orders is the same instance as in open_orders before deletion
        setattr(order, 'status', 'CANCELLED')
        setattr(order, 'cancelled_timestamp', self.current_time)
        
        del self.open_orders[order_id]
        
        self.logger.info(f"Order {order_id} cancelled.")
        return True, "Order cancelled successfully"

    # --- Market Data Methods ---
    
    def set_current_bar(self, symbol: str, bar: 'Candle'):
        """
        Called by the backtesting engine to update the current bar for a symbol.
        """
        self.current_bars[symbol] = bar
        # Optionally, also update historical_data's last_price if structure is known
        # For example, if self.historical_data[symbol] = {'last_price': ...}
        if isinstance(self.historical_data, dict) and symbol in self.historical_data:
             if hasattr(bar, 'close'): # Check if bar has a close attribute
                self.historical_data[symbol]['last_price'] = getattr(bar, 'close')
        elif isinstance(self.historical_data, dict) and symbol not in self.historical_data:
             if hasattr(bar, 'close'):
                self.historical_data[symbol] = {'last_price': getattr(bar, 'close')}


    def get_historical_candles(self, symbol: str, timeframe: 'Timeframe', from_date: 'datetime', to_date: 'datetime') -> list['Candle']:
        if hasattr(self.historical_data, 'get_data') and callable(self.historical_data.get_data):
            # Assumes self.historical_data is a HistoricalDataManager instance
            return self.historical_data.get_data(symbol=symbol, timeframe=timeframe, from_date=from_date, to_date=to_date)
        elif isinstance(self.historical_data, dict):
            # Basic filtering if historical_data is a dict of lists of candles
            # This is a simplified fallback and might not be fully robust for all timeframe/date filtering.
            # For now, as per instruction, if it's a dict, delegation fails.
            # The actual HistoricalDataManager should handle complex filtering.
            self.logger.warning("get_historical_candles: historical_data is a dict, not a HistoricalDataManager. Returning empty list. Full filtering not implemented for dict.")
            # Example basic filtering (if self.historical_data[symbol] was a list of candles):
            # if symbol in self.historical_data and isinstance(self.historical_data[symbol], list):
            #     return [
            #         c for c in self.historical_data[symbol]
            #         if getattr(c, 'timestamp', None) >= from_date and getattr(c, 'timestamp', None) <= to_date
            #     ]
            return [] 
        else:
            self.logger.error("get_historical_candles: historical_data is not set or is not a HistoricalDataManager instance with get_data method.")
            return []

    def get_current_bar(self, symbol: str) -> 'Candle | None':
        bar = self.current_bars.get(symbol)
        if bar is None:
            self.logger.warning(f"No current bar data available for symbol: {symbol}")
        return bar

    def subscribe_market_data(self, symbols: list[str]) -> bool:
        self.logger.info(f"Subscribed to market data for symbols: {symbols}")
        # In a real client, this would involve actual subscription logic.
        # For mock, we just acknowledge.
        return True

    def subscribe_order_updates(self) -> bool:
        self.logger.info("Subscribed to order updates.")
        # Mock implementation, always successful.
        return True

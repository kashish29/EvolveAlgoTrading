import random
import logging
from datetime import datetime
from src.broker_api.base_broker_client import BaseBrokerClient
# Forward references for type hinting if needed
import pandas as pd
from typing import TYPE_CHECKING
from src.core.models import Order, Trade # Keep Order if used, or remove if not
from src.core.models import Timeframe, Candle # Ensure Candle and Timeframe are imported
from typing import Union, Dict, Any, Optional, List # Ensure List is here

class MockFyersClient(BaseBrokerClient):
    def __init__(self, 
                 historical_data: Union[Dict, Any] = None, # Can be HDM instance or dict
                 initial_cash: float = 100000.0,
                 commission_rate: float = 0.0002, # 0.02%
                 slippage_percent: float = 0.0001): # 0.01%
        self.current_time: Optional[datetime] = None
        self.initial_cash = initial_cash
        self.cash: float = initial_cash
        self.positions: dict = {}  # Stores symbol: {'quantity': int, 'average_price': float}
        self.open_orders: dict = {} # Stores order_id: Order
        self.all_orders: list = []    # Stores all Order objects, including historical
        self.trade_log: list = []     # Stores Trade objects or dicts representing trades
        self.order_id_counter: int = 0
        self.trade_id_counter: int = 0
        self.simulated_order_updates_log: List['Order'] = []
        self.portfolio_history: List[Dict[str, Any]] = [] # To store snapshots of portfolio value over time
        
        # historical_data can be an instance of HistoricalDataManager or a dict
        self.historical_data = historical_data if historical_data is not None else {}
        
        self.current_bars: dict = {} # Stores symbol: Candle for the current bar
        self.commission_rate: float = commission_rate
        self.slippage_percent: float = slippage_percent
        # Simple slippage model: price * (1 + slippage_percent) for buy, price * (1 - slippage_percent) for sell
        self.slippage_model = lambda price, side: price * (1 + self.slippage_percent) if side == "BUY" else price * (1 - self.slippage_percent)
        
        self.logger = logging.getLogger(self.__class__.__name__) # Use class name for logger
        # Basic config for logging, consider moving to a global config if app expands
        # or if not already configured by a higher-level module (like main.py)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger.info(f"MockFyersClient initialized with initial_cash: {initial_cash}, commission_rate: {commission_rate}, slippage_percent: {slippage_percent}.")

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


    def get_order_history(self, order_id: Optional[str] = None, status: Optional[str] = None) -> List['Order']:
        filtered_orders = self.all_orders
        if order_id is not None:
            # Assuming Order objects will have an 'id' attribute
            filtered_orders = [order for order in filtered_orders if getattr(order, 'id', None) == order_id]
        
        if status is not None:
            # Assuming Order objects will have a 'status' attribute
            filtered_orders = [order for order in filtered_orders if getattr(order, 'status', None) == status.upper()] # Assuming status might be compared case-insensitively or stored in upper
        
        return filtered_orders

    def get_trade_history(self, order_id: Optional[str] = None) -> List['Trade']:
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
        order_type_str = order_type_attr.value if order_type_attr else str(order_type_attr)
        order_type_processed = order_type_str.upper()

        order_symbol = getattr(order, 'symbol', None)
        order_quantity = getattr(order, 'quantity', 0)
        
        order_side_attr = getattr(order, 'side', None)
        order_side_str = order_side_attr.value if order_side_attr else str(order_side_attr)
        order_side_processed = order_side_str.upper()


        if not all([order_symbol, order_quantity > 0, order_side_processed in ["BUY", "SELL"], order_type_processed]):
            self.logger.error(f"Order validation failed: {order_symbol}, {order_quantity}, {order_side_processed}, {order_type_processed}")
            setattr(order, 'status', "REJECTED")
            setattr(order, 'reject_reason', "Invalid order parameters")
            self.all_orders.append(order) # Log rejected order
            # For non-market orders, REJECTED is a terminal state for the order lifecycle from client's perspective
            if order_type_processed != "MARKET":
                self.simulated_order_updates_log.append(order)
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
                if order_symbol is not None:
                    current_bar_data = self.get_current_bar(order_symbol)
                    if current_bar_data and current_bar_data.close is not None:
                        base_price = current_bar_data.close
                    else:
                        self.logger.warning(f"Could not get current bar data for {order_symbol} or close price is None. Using default price.")
                        base_price = random.uniform(99.5, 100.5) # Fallback price
                else:
                    self.logger.error(f"Order symbol is None for order {order_id}. Cannot get current bar data.")
                    setattr(order, 'status', "REJECTED")
                    setattr(order, 'reject_reason', "Missing order symbol")
                    self.all_orders.append(order)
                    self.simulated_order_updates_log.append(order)
                    return order_id, "REJECTED"
                    # Absolute fallback if no other price source is available
                    base_price = 100.00  # Default fallback price
                    self.logger.warning(
                        f"Market order {order_id} for {order_symbol}: "
                        f"last_price not in historical_data dict and no current bar available. "
                        f"Using default base_price: {base_price}."
                    )
            
            fill_price = self.slippage_model(base_price, order_side_processed) # Pass side to slippage model
            trade_value = fill_price * order_quantity
            commission = trade_value * self.commission_rate

            # Check for insufficient funds for BUY MARKET orders
            if order_side_processed == "BUY" and self.cash < (trade_value + commission):
                self.logger.warning(f"Market order {order_id} for {order_quantity} {order_symbol} REJECTED: Insufficient funds. Required: {trade_value + commission:.2f}, Available: {self.cash:.2f}")
                setattr(order, 'status', "REJECTED")
                setattr(order, 'reject_reason', "Insufficient funds")
                self.all_orders.append(order)
                # Market order rejections (like insufficient funds) might not go to simulated_order_updates_log
                # if the rejection is immediate and synchronous, as per the docstring of get_simulated_order_updates.
                # However, adding it here for consistency if some rejections are expected there.
                # Let's assume critical rejections like this are immediately returned and logged.
                # self.simulated_order_updates_log.append(order) 
                return order_id, "REJECTED"

            # Increment Trade ID & Create Trade Object
            self.trade_id_counter += 1
            trade = Trade(
                trade_id=f"mock_trade_{self.trade_id_counter}",
                order_id=order_id,
                symbol=str(order_symbol), # Ensure it's a string
                quantity=order_quantity,
                price=fill_price,
                side=order.side, # Directly use order.side which is OrderSide
                timestamp=self.current_time if self.current_time is not None else datetime.now(), # Ensure datetime
                commission=commission,
                pnl=0.0 # Initialize pnl for market orders
            )
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
                    "unrealized_pnl": 0.0, # Track unrealized PnL for open positions
                    "last_price": fill_price
                }
            
            current_pos = self.positions[order_symbol]
            realized_pnl = 0.0 # Initialize realized PnL for this trade

            if order_side_processed == "BUY":
                if current_pos['quantity'] < 0: # Closing a short position
                    quantity_to_cover = min(order_quantity, abs(current_pos['quantity']))
                    realized_pnl += (current_pos['average_price'] - fill_price) * quantity_to_cover
                    self.logger.debug(f"Realized PnL (covering short): {realized_pnl:.2f}")
                
                new_total_value = (current_pos['average_price'] * current_pos['quantity']) + (fill_price * order_quantity)
                current_pos['quantity'] += order_quantity
                current_pos['average_price'] = new_total_value / current_pos['quantity'] if current_pos['quantity'] != 0 else fill_price
            
            elif order_side_processed == "SELL":
                if current_pos['quantity'] > 0: # Closing a long position
                    quantity_to_close = min(order_quantity, current_pos['quantity'])
                    realized_pnl += (fill_price - current_pos['average_price']) * quantity_to_close
                    self.logger.debug(f"Realized PnL (closing long): {realized_pnl:.2f}")
                
                new_total_value = (current_pos['average_price'] * current_pos['quantity']) + (fill_price * -order_quantity) # Selling reduces value
                current_pos['quantity'] -= order_quantity
                current_pos['average_price'] = new_total_value / current_pos['quantity'] if current_pos['quantity'] != 0 else fill_price
            
            current_pos['last_price'] = fill_price
            # Update unrealized PnL (simple calculation based on last price)
            if current_pos['quantity'] != 0:
                current_pos['unrealized_pnl'] = (current_pos['last_price'] - current_pos['average_price']) * current_pos['quantity']
            else:
                current_pos['unrealized_pnl'] = 0.0


            # Add realized PnL to the trade object
            setattr(trade, 'pnl', realized_pnl)

            # Update Order Status
            setattr(order, 'status', "COMPLETED")
            setattr(order, 'filled_timestamp', self.current_time)
            setattr(order, 'executed_price', fill_price)
            setattr(order, 'commission', commission) # Store commission on order too
            setattr(order, 'pnl', realized_pnl) # Store realized PnL on the order object

            self.all_orders.append(order)
            self.logger.info(f"Market order {order_id} for {order_quantity} {order_symbol} @ {fill_price:.2f} COMPLETED. Realized PnL: {realized_pnl:.2f}")
            return order_id, "COMPLETED"
        
        elif order_type_processed in ["LIMIT", "STOP"]: # Use processed string
            required_price_attr = 'price' if order_type_processed == "LIMIT" else 'trigger_price'
            if getattr(order, required_price_attr, None) is None:
                self.logger.error(f"{order_type_processed} order {order_id} for {order_symbol} REJECTED: Missing {required_price_attr}.")
                setattr(order, 'status', "REJECTED")
                setattr(order, 'reject_reason', f"Missing {required_price_attr}")
                self.all_orders.append(order)
                self.simulated_order_updates_log.append(order) # Add to the new log
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
            self.simulated_order_updates_log.append(order) # Add to the new log
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
                    actual_fill_price = self.slippage_model(base_fill_price, order_side_processed) # Pass side
                    executed = True
                    self.logger.info(f"STOP BUY order {order_id} for {order_symbol} triggered at {trigger_price:.2f} (bar high: {bar_high:.2f}). Base fill: {base_fill_price:.2f}, Slippage fill: {actual_fill_price:.2f}")
                elif order_side_processed == "SELL" and bar_low <= trigger_price:
                    # Stop Sell triggered, execute as market
                    base_fill_price = min(bar_open, trigger_price)
                    actual_fill_price = self.slippage_model(base_fill_price, order_side_processed) # Pass side
                    executed = True
                    self.logger.info(f"STOP SELL order {order_id} for {order_symbol} triggered at {trigger_price:.2f} (bar low: {bar_low:.2f}). Base fill: {base_fill_price:.2f}, Slippage fill: {actual_fill_price:.2f}")

            if executed and actual_fill_price is not None:
                trade_value = actual_fill_price * order_quantity
                commission = trade_value * self.commission_rate


                # Increment Trade ID & Create Trade Object
                self.trade_id_counter += 1
                trade = Trade(
                    trade_id=f"mock_trade_{self.trade_id_counter}",
                    order_id=order_id,
                    symbol=str(order_symbol), # Ensure it's a string
                    quantity=order_quantity,
                    price=actual_fill_price,
                    side=order.side, # Directly use order.side which is OrderSide
                    timestamp=bar_timestamp, # bar_timestamp is already datetime
                    commission=commission,
                    pnl=0.0 # Initialize pnl for pending orders
                )
                self.trade_log.append(trade)

                # Update Cash
                if order_side_processed == "BUY":
                    self.cash -= (trade_value + commission)
                elif order_side_processed == "SELL":
                    self.cash += (trade_value - commission)


                # Update Positions (reusing logic similar to MARKET orders)
                if order_symbol not in self.positions:
                    self.positions[order_symbol] = {"symbol": order_symbol, "quantity": 0, "average_price": 0.0, "unrealized_pnl": 0.0, "last_price": actual_fill_price}
                
                current_pos = self.positions[order_symbol]
                realized_pnl = 0.0 # Initialize realized PnL for this trade

                if order_side_processed == "BUY":
                    if current_pos['quantity'] < 0: # Closing a short position
                        quantity_to_cover = min(order_quantity, abs(current_pos['quantity']))
                        realized_pnl += (current_pos['average_price'] - actual_fill_price) * quantity_to_cover
                        self.logger.debug(f"Realized PnL (covering short): {realized_pnl:.2f}")
                    
                    new_total_value = (current_pos['average_price'] * current_pos['quantity']) + (actual_fill_price * order_quantity)
                    current_pos['quantity'] += order_quantity
                    current_pos['average_price'] = new_total_value / current_pos['quantity'] if current_pos['quantity'] != 0 else actual_fill_price
                
                elif order_side_processed == "SELL":
                    if current_pos['quantity'] > 0: # Closing a long position
                        quantity_to_close = min(order_quantity, current_pos['quantity'])
                        realized_pnl += (actual_fill_price - current_pos['average_price']) * quantity_to_close
                        self.logger.debug(f"Realized PnL (closing long): {realized_pnl:.2f}")
                    
                    new_total_value = (current_pos['average_price'] * current_pos['quantity']) + (actual_fill_price * -order_quantity) # Selling reduces value
                    current_pos['quantity'] -= order_quantity
                    current_pos['average_price'] = new_total_value / current_pos['quantity'] if current_pos['quantity'] != 0 else actual_fill_price
                
                current_pos['last_price'] = actual_fill_price
                # Update unrealized PnL
                if current_pos['quantity'] != 0:
                    current_pos['unrealized_pnl'] = (current_pos['last_price'] - current_pos['average_price']) * current_pos['quantity']
                else:
                    current_pos['unrealized_pnl'] = 0.0

                # Add realized PnL to the trade object
                setattr(trade, 'pnl', realized_pnl)

                # Update Order Status
                setattr(order, 'status', "COMPLETED")
                setattr(order, 'executed_price', actual_fill_price)
                setattr(order, 'filled_timestamp', bar_timestamp)
                setattr(order, 'commission', commission)
                setattr(order, 'pnl', realized_pnl) # Store realized PnL on the order object
                
                self.simulated_order_updates_log.append(order) # Add to the new log
                del self.open_orders[order_id]
                self.logger.info(f"{order_type_processed} order {order_id} for {order_quantity} {order_symbol} @ {actual_fill_price:.2f} COMPLETED. Commission: {commission:.2f}. Realized PnL: {realized_pnl:.2f}")



    def modify_order(self, order_id: str, new_price: Optional[float] = None, new_quantity: Optional[int] = None, new_trigger_price: Optional[float] = None) -> tuple[bool, str]:
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
        
        self.simulated_order_updates_log.append(order) # Add to the new log
        del self.open_orders[order_id]
        
        self.logger.info(f"Order {order_id} cancelled.")
        return True, "Order cancelled successfully"

    # --- Market Data Methods ---
    
    def set_current_bar(self, symbol: str, bar: Any): # bar is 'Candle'
        """
        Called by the backtesting engine to update the current bar for a symbol.
        """
        self.current_bars[symbol] = bar
        # Update last_price in positions if symbol exists
        if symbol in self.positions and hasattr(bar, 'close'):
            self.positions[symbol]['last_price'] = getattr(bar, 'close')
        # Also update historical_data if it's a dict and being used to store last_price (less common for this mock)
        if isinstance(self.historical_data, dict) and symbol in self.historical_data:
             if hasattr(bar, 'close'):
                if isinstance(self.historical_data[symbol], dict): # If historical_data stores dicts per symbol
                    self.historical_data[symbol]['last_price'] = getattr(bar, 'close')
        elif isinstance(self.historical_data, dict) and symbol not in self.historical_data:
             if hasattr(bar, 'close'):
                 self.historical_data[symbol] = {'last_price': getattr(bar, 'close')}


    def get_historical_data(self, symbol: str, timeframe: str, 
                            start_date: datetime, end_date: datetime) -> Optional[List[Dict[str, Any]]]:
        """
        Mock method to return historical data.
        If self.historical_data is a dict {symbol: [list_of_candle_dicts_or_objects]}, it filters from there.
        Otherwise, returns a default mock data structure or empty list.
        The HistoricalDataManager expects a DataFrame, but this mock can return list of dicts
        which HDM would then convert. Or this can directly return a DataFrame.
        For simplicity with test_engine.py providing sample_candles (list of Candle objects),
        this method will filter that if available.
        """
        self.logger.info(f"MockFyersClient: get_historical_data called for {symbol} from {start_date} to {end_date}.")
        
        data_to_return = []
        
        if isinstance(self.historical_data, dict) and symbol in self.historical_data:
            # Assuming self.historical_data is like data_feeds: {symbol: [Candle_objects]}
            all_symbol_candles = self.historical_data.get(symbol, [])
            
            for candle_obj in all_symbol_candles:
                candle_timestamp = getattr(candle_obj, 'timestamp', None)
                if candle_timestamp and start_date <= candle_timestamp <= end_date:
                    # Convert Candle object to dict as broker APIs often return list of dicts
                    data_to_return.append({
                        "timestamp": candle_timestamp,
                        "open": getattr(candle_obj, 'open', 0),
                        "high": getattr(candle_obj, 'high', 0),
                        "low": getattr(candle_obj, 'low', 0),
                        "close": getattr(candle_obj, 'close', 0),
                        "volume": getattr(candle_obj, 'volume', 0),
                        "symbol": symbol, # Add symbol and timeframe for completeness
                        "timeframe": timeframe
                    })
            self.logger.info(f"MockFyersClient: Returning {len(data_to_return)} pre-loaded bars for {symbol}.")
            return data_to_return
        
        # Fallback: If no specific data is pre-loaded for the symbol, generate some generic mock data
        # This part is more for if MockFyersClient is used without pre-loaded data.
        # For test_engine.py, the pre-loaded path should be taken.
        self.logger.warning(f"MockFyersClient: No pre-loaded data for {symbol}. Generating generic data.")
        dates = pd.date_range(start_date, end_date, freq='D') # Assuming daily for generic
        if not len(dates): return []
        
        for date_ts in dates:
            data_to_return.append({
                "timestamp": date_ts,
                "open": random.uniform(90,100),
                "high": random.uniform(100,110),
                "low": random.uniform(80,90),
                "close": random.uniform(90,100),
                "volume": random.randint(1000,10000),
                "symbol": symbol,
                "timeframe": timeframe
            })
        return data_to_return

    def get_current_bar(self, symbol: str) -> Optional[Candle]: # Returns 'Candle | None'
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

    def get_historical_candles(self, symbol: str, timeframe: Timeframe, 
                               from_date: datetime, to_date: datetime) -> List[Candle]:
        self.logger.info(f"MockFyersClient: get_historical_candles called for {symbol} ({timeframe.value if isinstance(timeframe, Timeframe) else timeframe}) from {from_date} to {to_date}.")
        
        data_to_return: List[Candle] = []
        
        # Check if self.historical_data is a dict and contains the symbol's data
        # This structure is used in test_engine.py where historical_data is {symbol: {timeframe: [Candle_objects]}}
        if isinstance(self.historical_data, dict) and symbol in self.historical_data:
            symbol_timeframe_data = self.historical_data.get(symbol, {}) # Get dict of timeframes for symbol
            candles_for_specific_timeframe = symbol_timeframe_data.get(timeframe, []) # Get list for the requested timeframe
            
            for candle_obj in candles_for_specific_timeframe: # Iterate over the correct list of candles
                # Assuming candle_obj are actual Candle instances
                if not isinstance(candle_obj, Candle):
                    self.logger.warning(f"MockFyersClient: Item in historical_data for {symbol} at timeframe {timeframe} is not a Candle object: {type(candle_obj)}. Skipping.")
                    continue

                candle_timestamp = getattr(candle_obj, 'timestamp', None)
                
                # Perform date filtering
                if candle_timestamp and from_date <= candle_timestamp <= to_date:
                    # Optional: Timeframe matching. The input `timeframe` is an enum.
                    # Candle objects also have a `timeframe` attribute which should be a Timeframe enum.
                    if hasattr(candle_obj, 'timeframe') and isinstance(getattr(candle_obj, 'timeframe'), Timeframe):
                        if candle_obj.timeframe == timeframe:
                            data_to_return.append(candle_obj)
                        # else:
                        #    self.logger.debug(f"Skipping candle due to timeframe mismatch: expected {timeframe}, got {candle_obj.timeframe}")
                    # else: # Removed the else block: if timeframe attribute is missing or not a Timeframe enum, it's skipped.
                        # self.logger.warning(f"Candle for {symbol} at {candle_timestamp} missing valid timeframe attribute or not a Timeframe enum. Skipping.")
            
            self.logger.info(f"MockFyersClient: Returning {len(data_to_return)} pre-loaded Candle objects for {symbol} matching criteria.")
        else:
            self.logger.warning(f"MockFyersClient: No pre-loaded data for {symbol} in self.historical_data dict for get_historical_candles.")
            # Unlike get_historical_data, this method will not generate generic mock data.
            # It expects data to be specifically pre-loaded if it's to be returned.

        return data_to_return

    def get_simulated_order_updates(self) -> List['Order']:
        """
        Retrieves simulated order updates that occurred based on recent market data 
        (e.g., fills, cancellations, rejections for pending orders) and clears the internal log.
        
        Market orders are processed synchronously and their "COMPLETED" or "REJECTED" status
        is returned directly by place_order; they won't appear in this list unless rejected
        for reasons other than being a market order (which is rare for this mock).
        """
        updates_to_dispatch = list(self.simulated_order_updates_log) # Make a copy
        self.simulated_order_updates_log.clear() # Clear the log
        return updates_to_dispatch

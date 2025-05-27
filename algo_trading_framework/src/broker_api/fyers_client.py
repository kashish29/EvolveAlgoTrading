import pandas as pd
from datetime import datetime, timedelta
import time
import random
from typing import List, Dict, Optional, Any
from algo_trading_framework.src.core.models import Order, Candle, Position
from algo_trading_framework.src.core.enums import OrderStatus, TradeType, InstrumentType, OrderType

class MockFyersClient:
    def __init__(self, client_id: str, token: str, log_path: str = "logs/", pin: Optional[str] = None):
        self.client_id = client_id
        self.token = token
        self.pin = pin # Pin might be needed for some Fyers operations, good to have
        self.log_path = log_path # Fyers client often has logging
        self.is_connected = False
        self._mock_orders: Dict[str, Order] = {}
        self._mock_positions: Dict[str, Position] = {}
        self._order_id_counter = 0

        print(f"MockFyersClient initialized for client_id: {client_id}. Connection status: {self.is_connected}")

    def connect(self) -> bool:
        print("MockFyersClient: Attempting to connect...")
        time.sleep(0.1) # Simulate network latency
        if self.client_id and self.token:
            self.is_connected = True
            print("MockFyersClient: Connection successful.")
            return True
        else:
            print("MockFyersClient: Connection failed. Client ID or Token missing.")
            return False

    def get_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        if not self.is_connected:
            print("MockFyersClient: Not connected. Cannot fetch historical data.")
            return None

        print(f"MockFyersClient: Fetching historical data for {symbol} from {start_date} to {end_date} with timeframe {timeframe}...")
        time.sleep(0.2) # Simulate API call

        # Generate some mock data
        date_rng = pd.date_range(start=start_date, end=end_date, freq='D') # Daily for simplicity
        if timeframe.endswith("MIN"): # Basic support for minute data
            freq = f"{timeframe[:-3]}T"
            date_rng = pd.date_range(start=start_date, end=end_date, freq=freq)
        elif timeframe.endswith("H"):
            freq = f"{timeframe[:-1]}H"
            date_rng = pd.date_range(start=start_date, end=end_date, freq=freq)


        num_bars = len(date_rng)
        if num_bars == 0:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol', 'timeframe'])


        data = {
            'timestamp': date_rng,
            'open': [random.uniform(90, 110) + i*0.1 for i in range(num_bars)],
            'high': [random.uniform(100, 120) + i*0.15 for i in range(num_bars)],
            'low': [random.uniform(80, 100) + i*0.05 for i in range(num_bars)],
            'close': [random.uniform(90, 110) + i*0.1 for i in range(num_bars)],
            'volume': [random.randint(1000, 10000) for _ in range(num_bars)],
            'symbol': symbol,
            'timeframe': timeframe
        }
        df = pd.DataFrame(data)
        # Ensure 'high' is always >= 'open' and 'close', and 'low' <= 'open' and 'close'
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)

        print(f"MockFyersClient: Successfully generated {len(df)} bars of mock data for {symbol}.")
        return df

    def place_order(self, symbol: str, trade_type: TradeType, order_type: OrderType,
                    quantity: float, price: Optional[float] = None, stop_price: Optional[float] = None,
                    instrument_type: InstrumentType = InstrumentType.EQUITY,
                    product_type: str = "INTRADAY") -> Optional[str]: # Fyers uses product_type
        if not self.is_connected:
            print("MockFyersClient: Not connected. Cannot place order.")
            return None

        self._order_id_counter += 1
        order_id = f"mock_ord_{self._order_id_counter}_{int(time.time())}"
        
        print(f"MockFyersClient: Placing order for {symbol} - {trade_type.value} {quantity} @ {order_type.value}...")

        # Basic validation
        if order_type == OrderType.LIMIT and price is None:
            print("MockFyersClient: Price must be provided for LIMIT order.")
            # In a real client, this might raise an error or return a specific failure code
            return None 
        if (order_type == OrderType.STOP or order_type == OrderType.STOP_LIMIT) and stop_price is None:
            print("MockFyersClient: Stop price must be provided for STOP/STOP_LIMIT order.")
            return None

        new_order = Order(
            order_id=order_id,
            timestamp=datetime.now(),
            symbol=symbol,
            trade_type=trade_type,
            order_type=order_type,
            quantity=quantity,
            price=price, # For LIMIT orders, this is the limit price. For MARKET, it's None initially.
            stop_price=stop_price,
            status=OrderStatus.OPEN, # Simulate it goes to OPEN quickly
            instrument_type=instrument_type
            # Fyers specific params like product_type, validity etc. could be added if needed
        )
        self._mock_orders[order_id] = new_order
        
        # Simulate immediate fill for MARKET orders for simplicity in mock
        if order_type == OrderType.MARKET:
            fill_price = random.uniform(price - 0.5, price + 0.5) if price else random.uniform(99.5, 100.5) # Mock fill near desired or current price
            new_order.status = OrderStatus.FILLED
            new_order.filled_quantity = quantity
            new_order.average_fill_price = fill_price
            print(f"MockFyersClient: Market Order {order_id} for {symbol} filled at {fill_price}.")
            # Here you might also update mock positions
            self._update_mock_position_on_fill(new_order)

        print(f"MockFyersClient: Order {order_id} placed successfully for {symbol}. Status: {new_order.status.value}")
        return order_id

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            print("MockFyersClient: Not connected.")
            return None
        
        order = self._mock_orders.get(order_id)
        if order:
            # Simulate Fyers API response structure (simplified)
            print(f"MockFyersClient: Fetching status for order {order_id}...")
            time.sleep(0.05) # Simulate network latency
            # Simulate that a LIMIT order might get filled after some time
            if order.order_type == OrderType.LIMIT and order.status == OrderStatus.OPEN:
                if random.random() < 0.3: # 30% chance of getting filled
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.average_fill_price = order.price # Assume filled at limit price
                    print(f"MockFyersClient: Limit Order {order_id} for {order.symbol} now FILLED at {order.average_fill_price}.")
                    self._update_mock_position_on_fill(order)


            return {
                "id": order.order_id,
                "symbol": order.symbol,
                "qty": order.quantity,
                "filledQty": order.filled_quantity,
                "side": 1 if order.trade_type == TradeType.BUY else -1, # Fyers convention
                "type": 2 if order.order_type == OrderType.LIMIT else 1, # Fyers convention (1:MKT, 2:LMT, 3:SL-MKT, 4:SL-LMT)
                "status": self._map_status_to_fyers(order.status), # Map to Fyers status codes
                "averagePrice": order.average_fill_price,
                "message": "Order status fetched successfully"
            }
        else:
            print(f"MockFyersClient: Order {order_id} not found.")
            return None
            
    def _map_status_to_fyers(self, status: OrderStatus) -> int:
        # Simplified mapping to Fyers status codes
        # (Refer to Fyers API docs for actual codes)
        if status == OrderStatus.FILLED: return 2 # "traded" / filled
        if status == OrderStatus.OPEN: return 6 # "pending" / open
        if status == OrderStatus.CANCELLED: return 1 # "cancelled"
        if status == OrderStatus.REJECTED: return 5 # "rejected"
        return 6 # Default to pending

    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        if not self.is_connected:
            print("MockFyersClient: Not connected.")
            return None
        
        print("MockFyersClient: Fetching positions...")
        time.sleep(0.1)
        
        fyers_positions = []
        for symbol, pos in self._mock_positions.items():
            if pos.quantity != 0: # Only return open positions
                fyers_positions.append({
                    "symbol": pos.symbol,
                    "netQty": pos.quantity,
                    "avgPrice": pos.average_entry_price,
                    "realized_profit": pos.realized_pnl,
                    "unrealized_profit": pos.unrealized_pnl, # Would need mock market data to update this live
                    "productType": "INTRADAY" # Example
                })
        print(f"MockFyersClient: Found {len(fyers_positions)} open positions.")
        return fyers_positions

    def _update_mock_position_on_fill(self, filled_order: Order):
        symbol = filled_order.symbol
        if symbol not in self._mock_positions:
            self._mock_positions[symbol] = Position(
                symbol=symbol,
                instrument_type=filled_order.instrument_type or InstrumentType.EQUITY, # Default if not set on order
                quantity=0,
                average_entry_price=0
            )
        
        position = self._mock_positions[symbol]
        
        trade_qty = filled_order.filled_quantity
        trade_price = filled_order.average_fill_price or 0 # Should have fill price

        # Simplified P&L and position update logic for mock
        current_total_value = position.average_entry_price * position.quantity
        trade_value = trade_price * trade_qty

        if filled_order.trade_type == TradeType.BUY:
            if position.quantity >= 0: # Buying more or opening long
                new_quantity = position.quantity + trade_qty
                position.average_entry_price = (current_total_value + trade_value) / new_quantity if new_quantity != 0 else 0
            else: # Buying to cover short
                profit_from_cover = (-position.quantity * position.average_entry_price) - (trade_qty * trade_price) if abs(position.quantity) >= trade_qty else 0
                position.realized_pnl += profit_from_cover
                new_quantity = position.quantity + trade_qty
                if new_quantity == 0:
                    position.average_entry_price = 0
                elif new_quantity > 0: # Flipped to long
                    position.average_entry_price = trade_price

            position.quantity = new_quantity

        elif filled_order.trade_type == TradeType.SELL:
            if position.quantity <= 0: # Selling more short or opening short
                new_quantity = position.quantity - trade_qty
                # For short selling, avg price is price at which shares were sold short
                position.average_entry_price = (abs(current_total_value) + trade_value) / abs(new_quantity) if new_quantity != 0 else 0
            else: # Selling to close long
                profit_from_sale = (trade_qty * trade_price) - (position.average_entry_price * trade_qty) if position.quantity >= trade_qty else 0
                position.realized_pnl += profit_from_sale
                new_quantity = position.quantity - trade_qty
                if new_quantity == 0:
                    position.average_entry_price = 0
                elif new_quantity < 0: # Flipped to short
                    position.average_entry_price = trade_price
            
            position.quantity = new_quantity
        
        position.last_updated = datetime.now()
        print(f"MockFyersClient: Position for {symbol} updated: Qty={position.quantity}, AvgPrice={position.average_entry_price:.2f}, RealizedP&L={position.realized_pnl:.2f}")


    def close_connection(self):
        self.is_connected = False
        print("MockFyersClient: Connection closed.")

# Example Usage (can be removed or commented out for production)
if __name__ == '__main__':
    mock_client = MockFyersClient(client_id="test_client", token="test_token")
    mock_client.connect()

    if mock_client.is_connected:
        # Fetch historical data
        hist_data = mock_client.get_historical_data("SBIN-EQ", "1D", datetime(2023,1,1), datetime(2023,1,10))
        if hist_data is not None:
            print("\nHistorical Data:")
            print(hist_data.head())

        # Place orders
        print("\nPlacing Orders:")
        order_id1 = mock_client.place_order("RELIANCE-EQ", TradeType.BUY, OrderType.MARKET, quantity=10)
        order_id2 = mock_client.place_order("TCS-EQ", TradeType.SELL, OrderType.LIMIT, quantity=5, price=3200.00)
        
        # Check order status
        print("\nOrder Status:")
        if order_id1:
            print(mock_client.get_order_status(order_id1))
        if order_id2:
            status_ord2 = mock_client.get_order_status(order_id2) # Try to fill it
            print(status_ord2)
            if status_ord2 and status_ord2['status'] != 2: # If not filled
                 print(mock_client.get_order_status(order_id2)) # Try again, might get filled this time

        # Check positions
        print("\nPositions:")
        positions = mock_client.get_positions()
        if positions:
            for pos in positions:
                print(pos)
        
        mock_client.close_connection()

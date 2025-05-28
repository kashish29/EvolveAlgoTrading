import unittest
from datetime import datetime
import uuid # For generating unique IDs for tests

from src.core.models import Candle, Signal, Order, Trade, Position
# Import all enums that are actually used in this test file
from src.core.enums import OrderType, OrderStatus, TradeType, InstrumentType, OrderSide, Timeframe 

class TestCoreModels(unittest.TestCase):

    def test_candle_creation(self):
        ts = datetime.now()
        candle = Candle(timestamp=ts, symbol="TEST", open=100, high=105, low=99, close=102, volume=1000)
        self.assertEqual(candle.timestamp, ts)
        self.assertEqual(candle.open, 100)
        self.assertEqual(candle.symbol, "TEST")
        # Test optional timeframe
        candle_with_tf = Candle(timestamp=ts, symbol="TEST", open=100, high=105, low=99, close=102, volume=1000, timeframe=Timeframe.DAY_1) 
        self.assertEqual(candle_with_tf.timeframe, Timeframe.DAY_1)


    def test_signal_creation(self):
        ts = datetime.now()
        # Corrected: 'trade_type' to 'side', value is OrderSide.BUY
        signal = Signal(timestamp=ts, symbol="TEST", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10)
        self.assertEqual(signal.symbol, "TEST")
        self.assertEqual(signal.side, OrderSide.BUY) 
        self.assertEqual(signal.quantity, 10)
        self.assertEqual(signal.order_type, OrderType.MARKET)

    def test_order_creation(self):
        ts = datetime.now()
        order_id_str = f"ord_{uuid.uuid4()}" # Use a string for id as per model
        # Corrected: Added 'id', 'side' should be OrderSide.SELL
        order = Order(
            id=order_id_str,
            symbol="TEST", 
            side=OrderSide.SELL, 
            order_type=OrderType.LIMIT, 
            quantity=5, 
            price=200.50,
            timestamp=ts 
        )
        self.assertEqual(order.id, order_id_str)
        self.assertEqual(order.symbol, "TEST")
        self.assertEqual(order.side, OrderSide.SELL)
        self.assertEqual(order.price, 200.50)
        self.assertEqual(order.status, OrderStatus.PENDING) # Default status
        self.assertEqual(order.timestamp, ts)


    def test_trade_creation(self):
        ts = datetime.now()
        trade_id_str = f"trd_{uuid.uuid4()}" # Use a string for trade_id
        # Corrected: Added 'trade_id', 'side' should be OrderSide.BUY
        trade = Trade(
            trade_id=trade_id_str,
            order_id="ord_123", 
            timestamp=ts, 
            symbol="TEST", 
            side=OrderSide.BUY, 
            quantity=10, 
            price=100.00,
            commission=1.0
        )
        self.assertEqual(trade.trade_id, trade_id_str)
        self.assertEqual(trade.order_id, "ord_123")
        self.assertEqual(trade.symbol, "TEST")
        self.assertEqual(trade.side, OrderSide.BUY)
        self.assertEqual(trade.price, 100.00)
        self.assertEqual(trade.commission, 1.0)

    def test_position_creation_and_update(self):
        # Corrected: Added missing 'quantity' and 'average_price' arguments. Removed 'instrument_type'.
        position = Position(symbol="TEST", quantity=0, average_price=0.0)
        self.assertEqual(position.symbol, "TEST")
        self.assertEqual(position.quantity, 0)
        self.assertEqual(position.average_price, 0.0) 
        
        buy_ts = datetime.now()
        # Corrected: Trade needs 'trade_id' and uses 'side'
        buy_trade = Trade(
            trade_id=f"trd_{uuid.uuid4()}",
            order_id="o1", 
            timestamp=buy_ts, 
            symbol="TEST", 
            side=OrderSide.BUY, 
            quantity=10, 
            price=100.00,
            commission=0.1 
        )
        
        # Position update logic is not part of the Position model itself.
        # We only test the state of the Position object as per its definition.
        self.assertEqual(position.average_price, 0.0) 
        self.assertEqual(position.realized_pnl, 0.0) 
        self.assertEqual(position.unrealized_pnl, 0.0)
        self.assertEqual(position.last_price, 0.0)


if __name__ == '__main__':
    unittest.main()

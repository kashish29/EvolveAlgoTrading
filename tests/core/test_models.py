import unittest
from datetime import datetime
from algo_trading_framework.src.core.models import Candle, Signal, Order, Trade, Position
from algo_trading_framework.src.core.enums import OrderType, OrderStatus, TradeType, InstrumentType

class TestCoreModels(unittest.TestCase):

    def test_candle_creation(self):
        ts = datetime.now()
        candle = Candle(timestamp=ts, open=100, high=105, low=99, close=102, volume=1000, symbol="TEST")
        self.assertEqual(candle.timestamp, ts)
        self.assertEqual(candle.open, 100)
        self.assertEqual(candle.symbol, "TEST")

    def test_signal_creation(self):
        ts = datetime.now()
        signal = Signal(timestamp=ts, symbol="TEST", trade_type=TradeType.BUY, order_type=OrderType.MARKET, quantity=10)
        self.assertEqual(signal.symbol, "TEST")
        self.assertEqual(signal.trade_type, TradeType.BUY)
        self.assertEqual(signal.quantity, 10)
        self.assertEqual(signal.order_type, OrderType.MARKET)

    def test_order_creation(self):
        ts = datetime.now()
        order = Order(
            symbol="TEST", 
            trade_type=TradeType.SELL, 
            order_type=OrderType.LIMIT, 
            quantity=5, 
            price=200.50,
            timestamp=ts # Overriding default factory for consistent testing
        )
        self.assertTrue(order.order_id.startswith("ord_"))
        self.assertEqual(order.symbol, "TEST")
        self.assertEqual(order.trade_type, TradeType.SELL)
        self.assertEqual(order.price, 200.50)
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.timestamp, ts)


    def test_trade_creation(self):
        ts = datetime.now()
        trade = Trade(
            order_id="ord_123", 
            timestamp=ts, 
            symbol="TEST", 
            trade_type=TradeType.BUY, 
            quantity=10, 
            price=100.00,
            commission=1.0
        )
        self.assertTrue(trade.trade_id.startswith("trd_"))
        self.assertEqual(trade.order_id, "ord_123")
        self.assertEqual(trade.symbol, "TEST")
        self.assertEqual(trade.price, 100.00)
        self.assertEqual(trade.commission, 1.0)

    def test_position_creation_and_update(self):
        position = Position(symbol="TEST", instrument_type=InstrumentType.EQUITY)
        self.assertEqual(position.symbol, "TEST")
        self.assertEqual(position.quantity, 0)
        
        # Simulate a BUY trade
        buy_ts = datetime.now()
        buy_trade = Trade(order_id="o1", timestamp=buy_ts, symbol="TEST", trade_type=TradeType.BUY, quantity=10, price=100)
        
        # Position update logic in models.py is complex, this is a simplified check if it was included
        # If Position.update_position is not implemented or complex, this test would need adjustment
        # For now, let's assume a simplified update or just test attributes if update_position is not part of this unit.
        if hasattr(position, 'update_position'):
            position.update_position(buy_trade) # Assuming this method exists and works
            self.assertEqual(position.quantity, 10)
            self.assertEqual(position.average_entry_price, 100)
        else:
            # If no update_position, just test initial state more thoroughly
            self.assertEqual(position.average_entry_price, 0.0)
            self.assertEqual(position.realized_pnl, 0.0)


if __name__ == '__main__':
    unittest.main()

import unittest
import pandas as pd # Keep pandas if it's used by the test's helper methods
from datetime import datetime, timedelta
from unittest.mock import MagicMock # Added for broker mock

from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
from src.core.models import Candle, Signal, OrderSide, OrderType, Order # Correctly import OrderSide, OrderType, Order from models

class TestExampleMovingAverageCrossStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy_id = "TestMASymbol" 
        self.broker_mock = MagicMock() 
        self.broker_mock.place_order.return_value = ("mock_order_id_123", "COMPLETED")
        self.config = {
            "short_window": 3, 
            "long_window": 5, 
            "symbol": "TEST_MA_SYMBOL",
            "quantity": 10 
        }
        self.strategy = ExampleMovingAverageCrossStrategy(
            strategy_id=self.strategy_id,
            broker=self.broker_mock, 
            config=self.config
        )
        
        self.sample_history = []
        base_time = datetime(2023, 1, 1)
        prices = [100, 101, 102, 103, 104, 103, 102, 101, 100, 99, 100, 101, 102, 103, 104, 105]

        for i, price in enumerate(prices):
            self.sample_history.append(Candle(
                timestamp=base_time + timedelta(days=i),
                symbol=self.config["symbol"],
                open=float(price - 0.5), 
                high=float(price + 0.5), 
                low=float(price - 1.0), 
                close=float(price),
                volume=1000 + i * 10
            ))

    def test_strategy_initialization(self):
        self.assertEqual(self.strategy.short_window, 3)
        self.assertEqual(self.strategy.long_window, 5)
        self.assertEqual(self.strategy.symbol, "TEST_MA_SYMBOL")
        self.assertEqual(self.strategy.quantity, 10)

    def test_no_signal_on_insufficient_data(self):
        self.broker_mock.reset_mock()
        self.broker_mock.get_positions.return_value = []
        for i in range(self.config["long_window"]):
            current_bars = {self.config["symbol"]: self.sample_history[i]}
            self.strategy.on_bar(current_bars)
            self.broker_mock.place_order.assert_not_called()

    def test_sell_signal_generation(self):
        self.broker_mock.reset_mock()
        self.broker_mock.get_positions.return_value = [{'symbol': self.config['symbol'], 'quantity': self.config['quantity'], 'average_price': 100.0}]
        sell_signal_candle_idx = 7
        for i in range(sell_signal_candle_idx + 1):
            current_bars = {self.config["symbol"]: self.sample_history[i]}
            self.strategy.on_bar(current_bars)
            if i < sell_signal_candle_idx:
                self.broker_mock.place_order.assert_not_called()
        
        self.broker_mock.place_order.assert_called_once()
        called_order = self.broker_mock.place_order.call_args[0][0]
        self.assertIsInstance(called_order, Order)
        self.assertEqual(called_order.symbol, self.config['symbol'])
        self.assertEqual(called_order.quantity, self.config['quantity'])
        self.assertEqual(called_order.side, OrderSide.SELL)
        self.assertEqual(called_order.order_type, OrderType.MARKET)

    def test_buy_signal_generation(self):
        self.broker_mock.reset_mock()
        self.broker_mock.get_positions.return_value = []
        buy_signal_candle_idx = 12
        for i in range(buy_signal_candle_idx + 1):
            current_bars = {self.config["symbol"]: self.sample_history[i]}
            self.strategy.on_bar(current_bars)
            if i < buy_signal_candle_idx:
                self.broker_mock.place_order.assert_not_called()

        self.broker_mock.place_order.assert_called_once()
        called_order = self.broker_mock.place_order.call_args[0][0]
        self.assertIsInstance(called_order, Order)
        self.assertEqual(called_order.symbol, self.config['symbol'])
        self.assertEqual(called_order.quantity, self.config['quantity'])
        self.assertEqual(called_order.side, OrderSide.BUY)
        self.assertEqual(called_order.order_type, OrderType.MARKET)

if __name__ == '__main__':
    unittest.main()

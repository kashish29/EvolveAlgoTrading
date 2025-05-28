import unittest
import pandas as pd # Keep pandas if it's used by the test's helper methods
from datetime import datetime, timedelta
from unittest.mock import MagicMock # Added for broker mock

from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
from src.core.models import Candle, Signal, OrderSide # Correctly import OrderSide from models
from src.core.enums import TradeType # TradeType is fine here

class TestExampleMovingAverageCrossStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy_id = "TestMASymbol" 
        self.broker_mock = MagicMock() 
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
        signal = None
        for i in range(self.config["long_window"]): 
            current_bars = {self.config["symbol"]: self.sample_history[i]}
            signal = self.strategy.on_bar(current_bars)
            if i < self.config["long_window"]: 
                 self.assertIsNone(signal, f"Signal should be None at bar index {i} as prev MAs not yet stable.")

    def test_sell_signal_generation(self):
        sell_signal_candle_idx = 7
        signal = None
        for i in range(sell_signal_candle_idx + 1):
            current_bars = {self.config["symbol"]: self.sample_history[i]}
            signal = self.strategy.on_bar(current_bars)
            if i < sell_signal_candle_idx:
                self.assertIsNone(signal, f"No signal expected at index {i}")
        
        self.assertIsNotNone(signal, f"Signal should be generated for SELL at index {sell_signal_candle_idx}.")
        if signal: 
            self.assertEqual(signal.symbol, self.config["symbol"])
            # The ExampleMovingAverageCrossStrategy creates an Order object with a 'side' attribute
            # The Signal object itself might have 'trade_type' or 'side'.
            # Let's assume the Signal object uses 'trade_type' which corresponds to TradeType.SELL
            self.assertEqual(signal.trade_type, TradeType.SELL) 
            self.assertEqual(signal.quantity, self.config["quantity"])

    def test_buy_signal_generation(self):
        buy_signal_candle_idx = 12
        signal = None
        for i in range(buy_signal_candle_idx + 1):
            current_bars = {self.config["symbol"]: self.sample_history[i]}
            signal = self.strategy.on_bar(current_bars)
            if i < buy_signal_candle_idx:
                self.assertIsNone(signal, f"No signal expected at index {i} for BUY test.")

        self.assertIsNotNone(signal, f"Signal should be generated for BUY at index {buy_signal_candle_idx}.")
        if signal: 
            self.assertEqual(signal.symbol, self.config["symbol"])
            self.assertEqual(signal.trade_type, TradeType.BUY)
            self.assertEqual(signal.quantity, self.config["quantity"])

if __name__ == '__main__':
    unittest.main()

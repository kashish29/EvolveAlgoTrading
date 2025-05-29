import unittest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone
import numpy as np # For SMA calculation comparison

from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
from src.core.models import Candle, Order
from src.core.enums import OrderType, OrderSide

class TestExampleMovingAverageCrossStrategy(unittest.TestCase):
    """
    Test suite for the ExampleMovingAverageCrossStrategy class.
    """

    def setUp(self):
        self.mock_broker = MagicMock()
        self.symbol = "TEST_SYM"
        self.short_window = 3
        self.long_window = 5
        self.quantity = 10
        
        self.strategy_config = {
            'symbol': self.symbol,
            'short_window': self.short_window,
            'long_window': self.long_window,
            'quantity': self.quantity
        }
        self.strategy = ExampleMovingAverageCrossStrategy(
            broker_client=self.mock_broker,
            config=self.strategy_config
        )
        # Reset internal state for each test if necessary (strategy should ideally handle this or be fresh)
        self.strategy.prices = []
        self.strategy.short_ma_values = []
        self.strategy.long_ma_values = []
        self.strategy.current_position = 0

    def _create_candle(self, timestamp: datetime, close_price: float, open_p=None, high_p=None, low_p=None, volume_p=None) -> Candle:
        return Candle(
            timestamp=timestamp,
            symbol=self.symbol,
            open=open_p if open_p is not None else close_price - 1,
            high=high_p if high_p is not None else close_price + 1,
            low=low_p if low_p is not None else close_price - 2,
            close=close_price,
            volume=volume_p if volume_p is not None else 1000
        )

    # Test Case 1: _calculate_sma() Method
    def test_calculate_sma(self):
        # a. Insufficient data
        self.assertIsNone(self.strategy._calculate_sma([10, 20], 3), "SMA with insufficient data should be None.")
        
        # b. Sufficient data
        prices1 = [10, 11, 12, 13, 14]
        self.assertAlmostEqual(self.strategy._calculate_sma(prices1, 3), np.mean([12, 13, 14]))
        self.assertAlmostEqual(self.strategy._calculate_sma(prices1, 5), np.mean(prices1))
        
        prices2 = [20, 22, 24, 20, 26, 28, 30]
        self.assertAlmostEqual(self.strategy._calculate_sma(prices2, 4), np.mean([20, 26, 28, 30]))

    # Test Case 2: on_bar() - Indicator Calculation Part
    def test_on_bar_indicator_calculation(self):
        # Feed enough candles to generate long MA values
        timestamps = [datetime(2023, 1, i, 10, tzinfo=timezone.utc) for i in range(1, 7)] # 6 candles
        close_prices = [10, 11, 12, 13, 14, 15] # Prices for these candles
        
        for i in range(len(timestamps)):
            candle = self._create_candle(timestamps[i], close_prices[i])
            self.strategy.on_bar(candle)

        self.assertEqual(len(self.strategy.prices), len(close_prices))
        self.assertEqual(self.strategy.prices, close_prices)
        
        # Short MA (window 3) calculations:
        # Prices: [10, 11, 12, 13, 14, 15]
        # Bar 3 (idx 2): MA([10,11,12]) = 11
        # Bar 4 (idx 3): MA([11,12,13]) = 12
        # Bar 5 (idx 4): MA([12,13,14]) = 13
        # Bar 6 (idx 5): MA([13,14,15]) = 14
        expected_short_ma = [np.nan, np.nan, 11.0, 12.0, 13.0, 14.0] # Padded with NaNs for non-calculable start
        
        # Long MA (window 5) calculations:
        # Bar 5 (idx 4): MA([10,11,12,13,14]) = 12
        # Bar 6 (idx 5): MA([11,12,13,14,15]) = 13
        expected_long_ma = [np.nan, np.nan, np.nan, np.nan, 12.0, 13.0]

        # Check internal state (assuming strategy stores MAs with NaNs for alignment or similar)
        # The actual storage might differ, this tests the concept.
        # If strategy only stores valid MAs, lengths and values would be different.
        # Based on typical strategy logic, they'd align with price length after padding.
        for i in range(len(self.strategy.prices)):
            if i < self.short_window -1 :
                self.assertTrue(np.isnan(self.strategy.short_ma_values[i]) if len(self.strategy.short_ma_values) > i else True)
            else:
                self.assertAlmostEqual(self.strategy.short_ma_values[i], expected_short_ma[i])
            
            if i < self.long_window -1:
                 self.assertTrue(np.isnan(self.strategy.long_ma_values[i]) if len(self.strategy.long_ma_values) > i else True)
            else:
                self.assertAlmostEqual(self.strategy.long_ma_values[i], expected_long_ma[i])

    # Test Case 3: on_bar() - BUY Order Generation Logic
    def test_on_bar_buy_order_generation(self):
        # Setup: prices and MAs so next bar causes BUY signal
        # Short MA needs to cross ABOVE Long MA
        # Previous state: Short MA <= Long MA
        # Current state:  Short MA > Long MA
        self.strategy.prices =       [10, 11, 12, 13, 10] # Ends with a dip to make long MA lower
        self.strategy.short_ma_values = [np.nan, np.nan, 11.0, 12.0, 11.666666] # (12+13+10)/3
        self.strategy.long_ma_values =  [np.nan, np.nan, np.nan, np.nan, 11.2] # (10+11+12+13+10)/5
        # Last values: Short MA (11.66) > Long MA (11.2) - this is already a buy signal.
        # Let's make previous values such that short_prev < long_prev
        
        # Simpler setup:
        # prices: [10,10,10,10,10] -> short_ma = 10, long_ma = 10
        # next candle: price = 15
        # new prices: [10,10,10,10,10,15]
        # new short_ma (idx 5): (10+10+15)/3 = 11.66
        # new long_ma (idx 5): (10+10+10+10+15)/5 = 11
        # Short MA (11.66) > Long MA (11) AND prev_short (10) == prev_long (10) -> BUY
        
        self.strategy.prices =          [10.0] * self.long_window # Fill up to long window
        self.strategy.short_ma_values = [10.0] * self.long_window # All MAs are 10 initially
        self.strategy.long_ma_values =  [10.0] * self.long_window
        self.strategy.current_position = 0 # No current position

        self.mock_broker.get_positions.return_value = [] # No existing position

        # Triggering candle
        buy_trigger_candle = self._create_candle(datetime(2023,1,self.long_window + 1, tzinfo=timezone.utc), 15.0)
        self.strategy.on_bar(buy_trigger_candle)

        self.mock_broker.place_order.assert_called_once()
        args, _ = self.mock_broker.place_order.call_args
        placed_order: Order = args[0]
        
        self.assertEqual(placed_order.symbol, self.symbol)
        self.assertEqual(placed_order.quantity, self.quantity)
        self.assertEqual(placed_order.side, OrderSide.BUY)
        self.assertEqual(placed_order.order_type, OrderType.MARKET)

        # Test if position exists, BUY is NOT called
        self.mock_broker.place_order.reset_mock()
        self.strategy.current_position = self.quantity # Simulate already in a long position
        # self.mock_broker.get_positions.return_value = [{'symbol': self.symbol, 'quantity': self.quantity, 'average_price': 10.0}]
        
        # Use the same MAs, but current_position is now non-zero
        # Need to re-feed the prices to update MAs correctly for this scenario, as on_bar modifies them
        self.strategy.prices =          [10.0] * self.long_window
        self.strategy.short_ma_values = [10.0] * self.long_window
        self.strategy.long_ma_values =  [10.0] * self.long_window
        
        self.strategy.on_bar(buy_trigger_candle) # Same triggering candle
        self.mock_broker.place_order.assert_not_called()


    # Test Case 4: on_bar() - SELL Order Generation Logic
    def test_on_bar_sell_order_generation(self):
        # Setup: prices and MAs so next bar causes SELL signal
        # Short MA needs to cross BELOW Long MA
        # Previous state: Short MA >= Long MA
        # Current state:  Short MA < Long MA
        
        # Simpler setup:
        # prices: [15,15,15,15,15] -> short_ma = 15, long_ma = 15
        # next candle: price = 10
        # new prices: [15,15,15,15,15,10]
        # new short_ma (idx 5): (15+15+10)/3 = 13.33
        # new long_ma (idx 5): (15+15+15+15+10)/5 = 14
        # Short MA (13.33) < Long MA (14) AND prev_short (15) == prev_long (15) -> SELL
        
        self.strategy.prices =          [15.0] * self.long_window
        self.strategy.short_ma_values = [15.0] * self.long_window
        self.strategy.long_ma_values =  [15.0] * self.long_window
        self.strategy.current_position = self.quantity # In a long position

        # self.mock_broker.get_positions.return_value = [{'symbol': self.symbol, 'quantity': self.quantity, 'average_price': 15.0}]

        # Triggering candle
        sell_trigger_candle = self._create_candle(datetime(2023,1,self.long_window + 1, tzinfo=timezone.utc), 10.0)
        self.strategy.on_bar(sell_trigger_candle)

        self.mock_broker.place_order.assert_called_once()
        args, _ = self.mock_broker.place_order.call_args
        placed_order: Order = args[0]
        
        self.assertEqual(placed_order.symbol, self.symbol)
        self.assertEqual(placed_order.quantity, self.quantity) # Sell the existing position quantity
        self.assertEqual(placed_order.side, OrderSide.SELL)
        self.assertEqual(placed_order.order_type, OrderType.MARKET)

        # Test if NO position exists, SELL is NOT called
        self.mock_broker.place_order.reset_mock()
        self.strategy.current_position = 0 # No current position
        # self.mock_broker.get_positions.return_value = []
        
        # Re-feed prices for MA calculation
        self.strategy.prices =          [15.0] * self.long_window
        self.strategy.short_ma_values = [15.0] * self.long_window
        self.strategy.long_ma_values =  [15.0] * self.long_window

        self.strategy.on_bar(sell_trigger_candle) # Same triggering candle
        self.mock_broker.place_order.assert_not_called()

if __name__ == '__main__':
    unittest.main()

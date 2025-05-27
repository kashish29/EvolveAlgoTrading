import unittest
import pandas as pd
from datetime import datetime, timedelta
from algo_trading_framework.src.strategies.example_strategy import ExampleMovingAverageCrossStrategy
from algo_trading_framework.src.core.models import Candle, Signal
from algo_trading_framework.src.core.enums import TradeType

class TestExampleMovingAverageCrossStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy_params = {"short_window": 3, "long_window": 5, "symbol": "TEST_MA"}
        self.strategy = ExampleMovingAverageCrossStrategy(params=self.strategy_params)
        
        # Create sample historical data
        self.sample_history = []
        base_time = datetime(2023, 1, 1)
        prices = [10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13] # Creates sell then buy signal
        for i, price in enumerate(prices):
            candle = Candle() # Using a simple object for Candle for test setup simplicity
            candle.timestamp=base_time + timedelta(days=i)
            candle.open=price
            candle.high=price + 0.5
            candle.low=price - 0.5
            candle.close=price
            candle.volume=100
            candle.symbol=self.strategy_params["symbol"]
            self.sample_history.append(candle)

    def _get_historical_df_up_to(self, current_idx: int) -> pd.DataFrame:
        """Helper to create a DataFrame from sample_history up to current_idx (exclusive)."""
        if current_idx == 0:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol'])
        
        history_for_df = self.sample_history[:current_idx]
        return pd.DataFrame([{
            'timestamp':c.timestamp, 'open':c.open, 'high':c.high, 'low':c.low, 'close':c.close, 
            'volume':c.volume, 'symbol':c.symbol
        } for c in history_for_df])


    def test_strategy_initialization(self):
        self.assertEqual(self.strategy.strategy_name, "MovingAverageCross") # Default name
        self.assertEqual(self.strategy.short_window, 3)
        self.assertEqual(self.strategy.long_window, 5)
        self.assertEqual(self.strategy.symbol, "TEST_MA")

    def test_no_signal_on_insufficient_data(self):
        # Not enough data for the long window
        current_candle = self.sample_history[self.strategy_params["long_window"] - 2]
        hist_df = self._get_historical_df_up_to(self.strategy_params["long_window"] - 2)
        signal = self.strategy.on_bar(current_candle, historical_data=hist_df)
        self.assertIsNone(signal)

    def test_sell_signal_generation(self):
        # Data is: 10, 11, 12, 13, 14 (long_window=5, short_window=3)
        # Bar 0: C=10
        # Bar 1: C=11
        # Bar 2: C=12. Short MA (10,11,12) = 11.
        # Bar 3: C=13. Short MA (11,12,13) = 12.
        # Bar 4: C=14. Short MA (12,13,14) = 13. Long MA (10,11,12,13,14) = 12. prevS=13, prevL=12 (BUY condition, S > L)
        # Need to run a few bars to set prev_short_ma and prev_long_ma
        
        # Prime the strategy with enough data to have prev_short_ma and prev_long_ma set
        # The crossover happens at index 6 (price 12) in self.sample_history
        # Prices: ..., 14 (idx 4), 13 (idx 5), 12 (idx 6)
        # At idx 4: S_MA(12,13,14)=13, L_MA(10,11,12,13,14)=12. prevS=13, prevL=12 (S > L)
        # At idx 5: S_MA(13,14,13)=13.33, L_MA(11,12,13,14,13)=12.6. prevS=13.33, prevL=12.6 (S > L)
        # At idx 6: S_MA(14,13,12)=13, L_MA(12,13,14,13,12)=12.8. (Still S > L based on current bar's numbers)
        # Let's re-evaluate the sequence for a clean crossover for test_example_strategy.py
        # Prices: 10, 11, 12, 13, 14, | 13, 12, 11, 10, 9, | 10, 11, 12, 13
        # Short Window: 3, Long Window: 5
        # Timestamp | Close | S_MA | L_MA | Prev_S | Prev_L | Signal
        # -------------------------------------------------------------------
        # idx 0 (d1)  | 10    | -    | -    | -      | -      | None
        # idx 1 (d2)  | 11    | -    | -    | -      | -      | None
        # idx 2 (d3)  | 12    | 11   | -    | -      | -      | None (prev MAs not set) -> strategy sets prev_short_ma=11, prev_long_ma=NaN
        # idx 3 (d4)  | 13    | 12   | -    | 11     | NaN    | None -> strategy sets prev_short_ma=12, prev_long_ma=NaN
        # idx 4 (d5)  | 14    | 13   | 12   | 12     | NaN    | None (L_MA just became valid) -> strategy sets prev_short_ma=13, prev_long_ma=12
        # idx 5 (d6)  | 13    | 13.33| 12.6 | 13     | 12     | BUY (13<=12 False, 13.33 > 12.6 True) -> prevS=13.33, prevL=12.6
        # idx 6 (d7)  | 12    | 13   | 12.8 | 13.33  | 12.6   | SELL (13.33>=12.6 True, 13 < 12.8 True) -> prevS=13, prevL=12.8
        
        sell_signal_candle_idx = 6 # This is where the sell signal should occur
        
        # Simulate calls for bars before the signal
        for i in range(sell_signal_candle_idx): # up to, but not including, sell_signal_candle_idx
            current_c = self.sample_history[i]
            hist_df = self._get_historical_df_up_to(i)
            # Call on_bar to update internal state (prev_short_ma, prev_long_ma)
            self.strategy.on_bar(current_c, historical_data=hist_df) 

        # Test the bar where signal is expected
        current_candle_for_signal = self.sample_history[sell_signal_candle_idx]
        hist_df_for_signal = self._get_historical_df_up_to(sell_signal_candle_idx)
        signal = self.strategy.on_bar(current_candle_for_signal, historical_data=hist_df_for_signal)
        
        self.assertIsNotNone(signal, f"Signal should be generated for SELL at index {sell_signal_candle_idx}.")
        if signal:
            self.assertEqual(signal.trade_type, TradeType.SELL)
            self.assertEqual(signal.symbol, self.strategy_params["symbol"])

    def test_buy_signal_generation(self):
        # Prices: ..., 11(idx7), 10(idx8), 9(idx9), | 10(idx10), 11(idx11) ...
        # Short Window: 3, Long Window: 5
        # Timestamp | Close | S_MA | L_MA | Prev_S | Prev_L | Signal
        # -------------------------------------------------------------------
        # ... (continuing from previous test's state at idx 6: prevS=13, prevL=12.8)
        # idx 7 (d8)  | 11    | 12   | 12   | 13     | 12.8   | None (13>=12.8 True, 12 < 12 False is False) -> prevS=12, prevL=12
        # idx 8 (d9)  | 10    | 11   | 12   | 12     | 12     | None (12>=12 True, 11 < 12 True) -> prevS=11, prevL=12  (This is actually a SELL signal by current logic)
                                                                    # The test data has a sell, then another sell, then a buy.
                                                                    # Let's re-evaluate the logic for buy: (prev_short_ma <= prev_long_ma and short_ma > long_ma)
        # idx 9 (d10) | 9     | 10   | 11.2 | 11     | 12     | None (11<=12 True, 10 > 11.2 False) -> prevS=10, prevL=11.2
        # idx 10 (d11)| 10    | 9.67 | 10.4 | 10     | 11.2   | None (10<=11.2 True, 9.67 > 10.4 False) -> prevS=9.67, prevL=10.4
        # idx 11 (d12)| 11    | 10   | 10   | 9.67   | 10.4   | BUY (9.67<=10.4 True, 10 > 10 False - but 10==10, so it's not strictly ">".)
                                                                    # The original logic `short_ma > long_ma` means it won't fire if they are equal.
                                                                    # For the prices [..., 9, 10, 11], S_MA(9,10,11) = 10. L_MA(...,10,9,10,11) - need L_MA for this.
                                                                    # L_MA for current candle at idx 11 (close=11): data for L_MA is (10,9,10,11, *from candle before, which is 10*)
                                                                    # prices up to idx 11 for L_MA: [...,11(idx7), 10(idx8), 9(idx9), 10(idx10), 11(idx11)]
                                                                    # L_MA(11,10,9,10,11) = 10.2
                                                                    # So at idx 11: S_MA = 10, L_MA = 10.2. prevS=9.67, prevL=10.4
                                                                    # Signal: (9.67 <= 10.4 AND 10 > 10.2) is (TRUE and FALSE) -> NO BUY SIGNAL
        # The sample data might need adjustment if current logic is strict `>`.
        # Let's use the provided prices and trace:
        # Prices: ..., 10, 9, 10, 11, 12, 13
        # idx 9: Price 9. S_MA(10,10,9) = 9.67. L_MA(12,11,10,10,9) = 10.4. prev_S=9.67, prev_L=10.4
        # idx 10: Price 10. S_MA(10,9,10) = 9.67. L_MA(11,10,10,9,10) = 10. prev_S=9.67, prev_L=10
        # idx 11: Price 11. S_MA(9,10,11) = 10. L_MA(10,10,9,10,11) = 10. prev_S=10, prev_L=10
        # idx 12: Price 12. S_MA(10,11,12) = 11. L_MA(10,9,10,11,12) = 10.4. prev_S=10, prev_L=10.4
        # BUY signal: (prev_S <= prev_L AND current_S > current_L)
        # At idx 12: prev_S=10, prev_L=10.4. current_S=11, current_L=10.4
        # (10 <= 10.4 AND 11 > 10.4) -> (TRUE AND TRUE) -> BUY SIGNAL.
        
        buy_signal_candle_idx = 12 # Adjusted based on re-trace
        
        # Simulate calls for bars before the signal
        for i in range(buy_signal_candle_idx):
            current_c = self.sample_history[i]
            hist_df = self._get_historical_df_up_to(i)
            self.strategy.on_bar(current_c, historical_data=hist_df)

        current_candle_for_signal = self.sample_history[buy_signal_candle_idx]
        hist_df_for_signal = self._get_historical_df_up_to(buy_signal_candle_idx)
        signal = self.strategy.on_bar(current_candle_for_signal, historical_data=hist_df_for_signal)

        self.assertIsNotNone(signal, f"Signal should be generated for BUY at index {buy_signal_candle_idx}.")
        if signal:
            self.assertEqual(signal.trade_type, TradeType.BUY)
            self.assertEqual(signal.symbol, self.strategy_params["symbol"])

if __name__ == '__main__':
    unittest.main()

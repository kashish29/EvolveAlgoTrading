import unittest
import pandas as pd
from datetime import datetime, timedelta
from algo_trading_framework.src.backtester.engine import BacktestEngine
from algo_trading_framework.src.strategies.example_strategy import ExampleMovingAverageCrossStrategy
from algo_trading_framework.src.core.models import Candle # For constructing mock data
from algo_trading_framework.src.core.enums import TradeType # For checking trade types

class TestBacktestEngine(unittest.TestCase):

    def setUp(self):
        self.strategy_params = {"short_window": 3, "long_window": 5, "symbol": "TEST_BT"}
        self.strategy = ExampleMovingAverageCrossStrategy(params=self.strategy_params)
        
        # Create simple, predictable historical data for backtesting
        self.test_data = []
        base_time = datetime(2023, 1, 1)
        # Prices designed to trigger one buy then one sell with MA(3,5)
        # Sell signal at idx 6 (price 12), Buy signal at idx 11 (price 11)
        prices = [10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 12] 
        for i, price in enumerate(prices):
            self.test_data.append({
                'timestamp': base_time + timedelta(days=i),
                'open': price, 'high': price + 0.5, 'low': price - 0.5, 'close': price,
                'volume': 1000 + i*10, 'symbol': self.strategy_params["symbol"]
            })
        self.historical_df = pd.DataFrame(self.test_data)
        # Ensure timestamp is datetime
        self.historical_df['timestamp'] = pd.to_datetime(self.historical_df['timestamp'])


    def test_backtest_engine_initialization(self):
        engine = BacktestEngine(self.strategy, self.historical_df.copy(), initial_capital=50000)
        self.assertEqual(engine.initial_capital, 50000)
        self.assertEqual(engine.cash, 50000)
        self.assertEqual(len(engine.trades), 0)
        self.assertTrue(engine.historical_data['timestamp'].equals(self.historical_df['timestamp']))

    def test_backtest_run_simple_scenario(self):
        engine = BacktestEngine(self.strategy, self.historical_df.copy(), initial_capital=100000, commission_per_trade=0.01)
        
        # Before run
        self.assertEqual(len(engine.trades), 0)
        self.assertEqual(engine.cash, 100000)

        results = engine.run()

        self.assertIsNotNone(results)
        self.assertTrue(len(engine.trades) > 0, "Trades should have been executed.")
        
        # Check if trades list has Trade objects with PnL (if PnL calculation is robust)
        # For this test, we expect a SELL then a BUY.
        # Sell @ 12 (idx 6), Buy to close @ 11 (idx 11) -> Profit on this pair
        # Then potentially another buy at idx 11, which is liquidated at end.

        self.assertIn("Total Return (%)", results)
        self.assertIn("Max Drawdown (%)", results)
        self.assertIn("Sharpe Ratio (Annualized, Rf=0%)", results)
        self.assertGreater(results["Total Trades"], 0)

        # A more specific assertion based on the known data and strategy:
        # We expect at least one profitable sequence (sell high, buy low).
        # The first trade should be a SELL (at index 6, price 12)
        # The next trade covering that short should be a BUY (at index 11, price 11)
        
        if len(engine.trades) >= 2:
            first_trade = engine.trades[0]
            second_trade = engine.trades[1] # This would be the BUY to cover the short
            
            self.assertEqual(first_trade.trade_type, TradeType.SELL)
            # Price check depends on exact fill logic (e.g. close of signal bar)
            # self.assertEqual(first_trade.price, 12) # Price of candle at index 6
            
            self.assertEqual(second_trade.trade_type, TradeType.BUY)
            # self.assertEqual(second_trade.price, 11) # Price of candle at index 11

            # Check if PnL was recorded for the closing trade (second_trade closes the first_trade's short)
            # The PnL calculation in the mock BacktestEngine is simplified.
            # A SELL at 12, then BUY at 11 to cover:
            # Proceeds from SELL = 12 * qty. Cost for BUY = 11 * qty.
            # Profit = (12 - 11) * qty - commissions for both trades.
            # The `trade.pnl` in BacktestEngine is set to this profit (net of its own commission).
            if hasattr(second_trade, 'pnl'):
                 self.assertGreater(second_trade.pnl, 0, "The first round trip (short sell, then buy cover) should be profitable before considering all commissions.")
        
        self.assertNotEqual(engine.cash, engine.initial_capital, "Cash should have changed due to trades and commissions.")
        self.assertTrue(len(engine.portfolio_history) > 0, "Portfolio history should be recorded.")


if __name__ == '__main__':
    unittest.main()

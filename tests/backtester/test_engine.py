import unittest
import datetime
import logging
import random # Import random

from src.backtester.engine import BacktesterEngine
from src.broker_api.mock_fyers_client import MockFyersClient
from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
# Adjusted import path for HistoricalDataManager
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.core.models import Candle, Timeframe, Order, OrderType, OrderSide # Order, OrderType, OrderSide might not be directly used here but good for context
from src.backtester.metrics import calculate_all_metrics

# Suppress or lower INFO messages during tests to keep output clean
logging.getLogger('src.broker_api.mock_fyers_client').setLevel(logging.WARNING)
logging.getLogger('MockFyersClient').setLevel(logging.WARNING) # If client uses class name
logging.getLogger('strategy.IntTest_MA_Cross').setLevel(logging.WARNING) # Strategy logger
logging.getLogger('src.backtester.engine').setLevel(logging.WARNING) # Engine logger


class TestBacktesterEngineIntegration(unittest.TestCase):

    def setUp(self):
        self.symbol = "INTEGRATION_TEST_SYMBOL"
        self.start_date = datetime.datetime(2023, 1, 1)
        self.end_date = datetime.datetime(2023, 1, 31) # Approx 30 days for daily data
        self.timeframe = Timeframe.DAY_1 
        self.initial_cash = 100000.0

        self.sample_candles: list[Candle] = []
        price = 100.0
        num_days = (self.end_date - self.start_date).days + 1
        
        for i in range(num_days):
            date = self.start_date + datetime.timedelta(days=i)
            # Create some trend for MA strategy
            if i < 10: price += 2  # Up trend for first 10 days
            elif i < 20: price -= 1 # Slight pullback for next 10 days
            else: price += 1.5    # Resume uptrend
            
            open_p = price - 0.5 + (random.uniform(-0.2, 0.2) * price) # Add some noise
            close_p = price + (random.uniform(-0.2, 0.2) * price)
            high_p = max(open_p, close_p) + random.uniform(0, 0.05) * price
            low_p = min(open_p, close_p) - random.uniform(0, 0.05) * price
            
            self.sample_candles.append(Candle(
                timestamp=date, symbol=self.symbol,
                open=open_p, high=high_p, low=low_p, close=close_p,
                volume=1000 + i*10, timeframe=self.timeframe
            ))
        
        data_feeds = {self.symbol: self.sample_candles}
        self.hdm = HistoricalDataManager()
        self.hdm.load_data(data_feeds)
        
        self.broker = MockFyersClient(
            historical_data=self.hdm, # Pass HDM instance
            initial_cash=self.initial_cash, 
            commission_rate=0.001 # 0.1% commission
        )
        
        # Strategy config: short_window=3, long_window=7 to ensure crossovers with ~30 days of data
        strategy_config = {
            "symbol": self.symbol, 
            "short_window": 3, 
            "long_window": 7, 
            "quantity": 10, 
            "timeframe": self.timeframe # Strategy might use this
        }
        self.strategy = ExampleMovingAverageCrossStrategy(
            strategy_id="IntTest_MA_Cross", 
            broker=self.broker, 
            config=strategy_config
        )
        
        self.engine = BacktesterEngine(
            strategy=self.strategy, 
            broker=self.broker, 
            historical_data_manager=self.hdm, 
            symbols=[self.symbol], # Changed from symbols_to_trade
            timeframe=self.timeframe.value, # Pass string value of timeframe
            start_date=self.start_date, 
            end_date=self.end_date
        )

    def test_full_backtest_run_and_basic_results(self):
        equity_curve, portfolio_history = self.engine.run()

        self.assertTrue(len(equity_curve) > 0, "Equity curve should not be empty.")
        # The first point in equity curve is initial cash as portfolio value is calculated at end of each bar,
        # even if no bar data for that first timestamp (engine loop starts with data)
        self.assertEqual(equity_curve[0], self.initial_cash, "First equity point should be initial cash.")
        
        self.assertTrue(len(portfolio_history) > 0, "Portfolio history should not be empty.")
        self.assertEqual(portfolio_history[0]['total_value'], self.initial_cash, "First portfolio history value should be initial cash.")

        trade_log = self.broker.get_trade_history() # List of trade dicts from MockFyersClient

        if not trade_log:
            # This might happen if data is too short or MA windows too large for crossovers
            logging.warning("No trades were executed with the sample data and strategy settings. Some metric verifications will be skipped.")
            # self.skipTest("No trades were executed. Cannot verify trade P&L or metrics fully.") # Optional: skip

        # Verify some portfolio history consistency
        if len(portfolio_history) > 1:
             self.assertTrue(
                 any(ph['cash'] != self.initial_cash for ph in portfolio_history[1:]), 
                 "Cash should change if trades or commissions occurred."
             )
             # positions_market_value can be 0 if position is squared off at end of day.
             # Check if it was ever non-zero if trades occurred.
             if trade_log:
                self.assertTrue(
                    any(ph['positions_market_value'] != 0 for ph in portfolio_history),
                    "Positions market value should be non-zero at some point if trades occurred."
                )
        
        # Test Metrics Calculation
        # The trade_log from MockFyersClient does not have 'pnl' per individual trade (fill).
        # PNL-based metrics like win_rate, profit_factor in calculate_win_rate_avg_win_loss_profit_factor
        # will not be meaningful if passed this raw trade_log.
        # We will rely on equity_curve based metrics more heavily.
        
        metrics = calculate_all_metrics(
            equity_curve=equity_curve, 
            trade_log=trade_log, # Pass the raw trade_log; PNL-specific metrics will be affected
            risk_free_rate_annual=0.02, 
            backtest_duration_days=(self.end_date - self.start_date).days + 1 # +1 for inclusive days
        )
        
        self.assertIn("total_return", metrics)
        self.assertIn("annualized_return", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("sortino_ratio", metrics)
        self.assertIn("max_drawdown", metrics)
        
        self.assertLessEqual(metrics["max_drawdown"], 1.0, "Max drawdown should be <= 1.0")
        self.assertGreaterEqual(metrics["max_drawdown"], 0.0, "Max drawdown should be >= 0.0")

        # These metrics will be 0 or not directly useful if 'pnl' is missing from trade_log items
        if trade_log:
            self.assertIn("win_rate", metrics) 
            self.assertIn("profit_factor", metrics)
            # Example: self.assertEqual(metrics["win_rate"], 0.0, "Win rate should be 0 if PNL not in trades")

        # Verify final portfolio value from equity curve matches calculated final value
        final_broker_balance = self.broker.get_balance()
        final_broker_positions = self.broker.get_positions() # List of dicts
        
        calculated_final_value = final_broker_balance['cash']
        if self.sample_candles: # Ensure there are candles to get the last price from
            last_event_timestamp = self.sample_candles[-1].timestamp
            for pos_dict in final_broker_positions:
                pos_symbol = pos_dict.get('symbol')
                pos_qty = pos_dict.get('quantity', 0)
                
                if pos_qty == 0: continue

                # Use the close of the last bar for this symbol for final valuation
                last_bar_for_pos = self.hdm.get_bar_at(pos_symbol, last_event_timestamp) # Timeframe ignored by current HDM
                
                last_price_for_valuation = pos_dict.get('last_price', 0.0) # Fallback to position's last known price
                if last_bar_for_pos and hasattr(last_bar_for_pos, 'close'):
                    last_price_for_valuation = last_bar_for_pos.close
                
                calculated_final_value += pos_qty * last_price_for_valuation
        
        self.assertAlmostEqual(equity_curve[-1], calculated_final_value, places=2, 
                               msg="Final equity from curve should match calculated final portfolio value.")

if __name__ == '__main__':
    unittest.main()

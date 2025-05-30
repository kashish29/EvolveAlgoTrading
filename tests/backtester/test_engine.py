import unittest
import datetime
import logging

# --- Preamble to resolve 'algo_trading_framework.src' to 'src' ---
import sys
import os
from unittest.mock import MagicMock, patch # Added patch

MOCK_ALGO_FRAMEWORK_NAME = 'algo_trading_framework'
MOCK_ALGO_FRAMEWORK_SRC_NAME = 'algo_trading_framework.src'

try:
    import src 
    
    if MOCK_ALGO_FRAMEWORK_NAME not in sys.modules:
        mock_algo_pkg = MagicMock(name=MOCK_ALGO_FRAMEWORK_NAME + "_mock")
        sys.modules[MOCK_ALGO_FRAMEWORK_NAME] = mock_algo_pkg
    else:
        mock_algo_pkg = sys.modules[MOCK_ALGO_FRAMEWORK_NAME]

    if not hasattr(mock_algo_pkg, 'src') or isinstance(getattr(mock_algo_pkg, 'src', None), MagicMock):
      mock_algo_pkg.src = src
    
    if MOCK_ALGO_FRAMEWORK_SRC_NAME not in sys.modules or isinstance(sys.modules[MOCK_ALGO_FRAMEWORK_SRC_NAME], MagicMock):
      sys.modules[MOCK_ALGO_FRAMEWORK_SRC_NAME] = src

    src_path_for_listing = os.path.dirname(src.__file__)
    for item_name in os.listdir(src_path_for_listing):
        item_path = os.path.join(src_path_for_listing, item_name)
        module_name_for_import = None
        if os.path.isdir(item_path) and "__init__.py" in os.listdir(item_path):
            module_name_for_import = item_name
        elif item_name.endswith('.py') and not item_name.startswith('__'):
            module_name_for_import = item_name[:-3]
        
        if module_name_for_import:
            actual_src_module_path = f"src.{module_name_for_import}"
            mocked_framework_module_path = f"{MOCK_ALGO_FRAMEWORK_SRC_NAME}.{module_name_for_import}"
            try:
                imported_actual_submodule = __import__(actual_src_module_path, fromlist=[module_name_for_import])
                setattr(mock_algo_pkg.src, module_name_for_import, imported_actual_submodule)
                if mocked_framework_module_path not in sys.modules or isinstance(sys.modules[mocked_framework_module_path], MagicMock):
                    sys.modules[mocked_framework_module_path] = imported_actual_submodule
            except ImportError:
                if mocked_framework_module_path not in sys.modules:
                    sys.modules[mocked_framework_module_path] = MagicMock(name=mocked_framework_module_path + "_mock")
                if hasattr(mock_algo_pkg.src, module_name_for_import) and isinstance(getattr(mock_algo_pkg.src, module_name_for_import, None), MagicMock) and getattr(mock_algo_pkg.src, module_name_for_import) is not sys.modules[mocked_framework_module_path] : # type: ignore
                    setattr(mock_algo_pkg.src, module_name_for_import, sys.modules[mocked_framework_module_path])
except ImportError as e:
    print(f"CRITICAL ERROR in test preamble for {__file__}: Could not import 'src' package directly. Error: {e}.")
    if MOCK_ALGO_FRAMEWORK_NAME not in sys.modules:
        sys.modules[MOCK_ALGO_FRAMEWORK_NAME] = MagicMock(name=MOCK_ALGO_FRAMEWORK_NAME + "_critical_fallback_mock")
    if MOCK_ALGO_FRAMEWORK_SRC_NAME not in sys.modules:
        sys.modules[MOCK_ALGO_FRAMEWORK_SRC_NAME] = MagicMock(name=MOCK_ALGO_FRAMEWORK_SRC_NAME + "_critical_fallback_mock")
# --- End Preamble ---

import random # Import random

from src.backtester.engine import BacktesterEngine
from src.broker_api.mock_fyers_client import MockFyersClient
from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
# Adjusted import path for HistoricalDataManager
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.data_handler.data_source_factory import DataSourceFactory # Added
from src.data_handler.data_cache import DataCache # Added
from src.data_handler.abstract_data_source import AbstractDataSource # Added for mock_source_instance spec
import pandas as pd # Added for DataFrame creation in mock
from src.core.models import Candle, Timeframe, Order, OrderType, OrderSide 
from src.backtester.metrics import calculate_all_metrics

# Suppress or lower INFO messages during tests to keep output clean
logging.getLogger('src.broker_api.mock_fyers_client').setLevel(logging.WARNING)
logging.getLogger('MockFyersClient').setLevel(logging.WARNING) 
logging.getLogger('strategy.IntTest_MA_Cross').setLevel(logging.WARNING) 
logging.getLogger('src.backtester.engine').setLevel(logging.WARNING) 


class TestBacktesterEngineIntegration(unittest.TestCase):

    def setUp(self):
        self.symbol = "INTEGRATION_TEST_SYMBOL"
        self.start_date = datetime.datetime(2023, 1, 1)
        self.end_date = datetime.datetime(2023, 1, 31) 
        self.timeframe = Timeframe.DAY_1 
        self.initial_cash = 100000.0

        self.sample_candles: list[Candle] = []
        price = 100.0
        num_days = (self.end_date - self.start_date).days + 1
        
        for i in range(num_days):
            date = self.start_date + datetime.timedelta(days=i)
            if i < 10: price += 2  
            elif i < 20: price -= 1 
            else: price += 1.5    
            
            open_p = price - 0.5 + (random.uniform(-0.2, 0.2) * price) 
            close_p = price + (random.uniform(-0.2, 0.2) * price)
            high_p = max(open_p, close_p) + random.uniform(0, 0.05) * price
            low_p = min(open_p, close_p) - random.uniform(0, 0.05) * price
            
            self.sample_candles.append(Candle(
                timestamp=date, symbol=self.symbol,
                open=open_p, high=high_p, low=low_p, close=close_p,
                volume=1000 + i*10, timeframe=self.timeframe
            ))
        
        data_feeds = {self.symbol: self.sample_candles}
        
        self.broker = MockFyersClient(
            historical_data=data_feeds, 
            initial_cash=self.initial_cash, 
            commission_rate=0.001 
        )

        # Mock dependencies for HistoricalDataManager
        self.mock_data_factory = MagicMock(spec=DataSourceFactory)
        self.mock_data_cache = MagicMock(spec=DataCache)
        
        # Instantiate HistoricalDataManager with new constructor
        # For this integration test, the actual source type and kwargs might not be deeply exercised
        # if the broker (MockFyersClient) is already providing all necessary data directly
        # or if get_all_data_sorted_by_timestamp is mocked/bypassed.
        # However, the engine *will* call hdm.get_all_data_sorted_by_timestamp, which calls hdm.fetch_historical_data.
        # So, we need to ensure that path can work with mocks if it doesn't find data in broker directly.
        # Let's provide basic mocks. The actual data comes from self.broker.historical_data via MockFyersClient's get_historical_data.
        # The BacktesterEngine._load_and_prepare_data calls self.historical_data_manager.get_all_data_sorted_by_timestamp.
        # The test's self.broker (MockFyersClient) needs to be accessible by HDM if we want it to act as a data source.
        # This test was originally designed with HDM using the broker directly.
        # Now, HDM uses its own sources. For this integration test to pass with minimal changes to its core logic,
        # we might need to have the mock_factory return a data source that uses self.broker.
        
        self.mock_data_cache.get_data.return_value = None # Ensure cache miss for initial fetch

        mock_source_instance = MagicMock(spec=AbstractDataSource) 
        
        # Configure the mock data source to return data based on self.broker's historical_data
        def mock_source_fetch_data(symbol, start_date, end_date, timeframe_str):
            # This simulates the data source fetching data, mimicking how MockFyersClient does it.
            raw_data = self.broker.get_historical_data(symbol, timeframe_str, start_date, end_date)
            if isinstance(raw_data, list): # MockFyersClient returns list of dicts
                return pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
            return raw_data # Or handle if it's already a DataFrame

        mock_source_instance.fetch_data.side_effect = mock_source_fetch_data
        self.mock_data_factory.get_data_source.return_value = mock_source_instance

        self.hdm = HistoricalDataManager(
            data_source_factory=self.mock_data_factory,
            data_cache=self.mock_data_cache,
            default_source_type="MOCK_BROKER_WRAPPER", # Dummy type
            default_source_kwargs={}
        )
        
        strategy_config = {
            "symbol": self.symbol, 
            "short_window": 3, 
            "long_window": 7, 
            "quantity": 10, 
            "timeframe": self.timeframe 
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
            symbols=[self.symbol], 
            timeframe=self.timeframe.value, 
            start_date=self.start_date, 
            end_date=self.end_date,
            generate_analytics_report=False # Explicitly set to False
        )

    # Patch PerformanceReporter here in case generate_analytics_report was True,
    # to prevent actual file I/O or external calls.
    # However, with generate_analytics_report=False in setUp, this patch is redundant 
    # for this specific test method but kept as an example if the flag was True.
    @patch('src.backtester.engine.PerformanceReporter') 
    def test_full_backtest_run_and_basic_results(self, MockPerformanceReporter):
        equity_curve, portfolio_history = self.engine.run()

        # If generate_analytics_report was False, PerformanceReporter should not have been called.
        if not self.engine.generate_analytics_report:
            MockPerformanceReporter.assert_not_called()

        self.assertTrue(len(equity_curve) > 0, "Equity curve should not be empty.")
        self.assertEqual(equity_curve[0], self.initial_cash, "First equity point should be initial cash.")
        
        self.assertTrue(len(portfolio_history) > 0, "Portfolio history should not be empty.")
        self.assertEqual(portfolio_history[0]['total_value'], self.initial_cash, "First portfolio history value should be initial cash.")

        trade_log = self.broker.get_trade_history() 

        if not trade_log:
            logging.warning("No trades were executed with the sample data and strategy settings. Some metric verifications will be skipped.")

        if len(portfolio_history) > 1:
             self.assertTrue(
                 any(ph['cash'] != self.initial_cash for ph in portfolio_history[1:]), 
                 "Cash should change if trades or commissions occurred."
             )
             if trade_log:
                self.assertTrue(
                    any(ph['positions_market_value'] != 0 for ph in portfolio_history),
                    "Positions market value should be non-zero at some point if trades occurred."
                )
        
        metrics = calculate_all_metrics(
            equity_curve=equity_curve, 
            trade_log=trade_log, 
            risk_free_rate_annual=0.02, 
            backtest_duration_days=(self.end_date - self.start_date).days + 1 
        )
        
        self.assertIn("total_return", metrics)
        self.assertIn("annualized_return", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("sortino_ratio", metrics)
        self.assertIn("max_drawdown", metrics)
        
        self.assertLessEqual(metrics["max_drawdown"], 1.0, "Max drawdown should be <= 1.0")
        self.assertGreaterEqual(metrics["max_drawdown"], 0.0, "Max drawdown should be >= 0.0")

        if trade_log:
            self.assertIn("win_rate", metrics) 
            self.assertIn("profit_factor", metrics)

        final_broker_balance = self.broker.get_balance()
        final_broker_positions = self.broker.get_positions() 
        
        calculated_final_value = final_broker_balance['cash']
        if self.sample_candles: 
            last_event_timestamp = self.sample_candles[-1].timestamp
            for pos_dict in final_broker_positions:
                pos_symbol = pos_dict.get('symbol')
                pos_qty = pos_dict.get('quantity', 0)
                
                if pos_qty == 0: continue


                # Use the close of the last bar for this symbol for final valuation
                last_bar_for_pos = None
                if pos_symbol == self.symbol and self.sample_candles and last_event_timestamp == self.sample_candles[-1].timestamp:
                    last_bar_for_pos = self.sample_candles[-1]
                # else:
                #    # Optional: log a warning if symbols don't match, though current test setup implies they will.
                #    logging.warning(f"Symbol mismatch or timestamp issue: pos_symbol={pos_symbol}, last_event_timestamp={last_event_timestamp}")

                last_price_for_valuation = pos_dict.get('last_price', 0.0) # Fallback
                if last_bar_for_pos and hasattr(last_bar_for_pos, 'close'):
                    last_price_for_valuation = last_bar_for_pos.close
                
                calculated_final_value += pos_qty * last_price_for_valuation
        
        self.assertAlmostEqual(equity_curve[-1], calculated_final_value, places=2, 
                               msg="Final equity from curve should match calculated final portfolio value.")

if __name__ == '__main__':
    unittest.main()

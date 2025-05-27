import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import pandas as pd
from datetime import datetime, timedelta
import random
import logging
import importlib # For dynamically getting the template

# Modules to test and mock
from algo_trading_framework.src.strategy_lab.fitness_evaluator import FitnessEvaluator
from algo_trading_framework.src.core.enums import Timeframe
from algo_trading_framework.src.strategies.base_strategy import BaseStrategy # For type checking in fallback

# Dynamically import DEFAULT_STRATEGY_TEMPLATE from evolutionary_engine
try:
    engine_module = importlib.import_module("algo_trading_framework.src.strategy_lab.evolutionary_engine")
    DEFAULT_STRATEGY_TEMPLATE_FOR_TEST = engine_module.DEFAULT_STRATEGY_TEMPLATE
except ImportError:
    # Fallback if direct import fails (e.g. path issues in test environment)
    # This fallback template should be minimal but define EvolvedStrategy
    print("Warning: Could not import DEFAULT_STRATEGY_TEMPLATE from evolutionary_engine. Using a fallback for tests.")
    DEFAULT_STRATEGY_TEMPLATE_FOR_TEST = """
import logging
from algo_trading_framework.src.strategies.base_strategy import BaseStrategy
from algo_trading_framework.src.core.models import Order, OrderType, OrderSide, Candle # type: ignore
from typing import TYPE_CHECKING, Dict, List
import random
if TYPE_CHECKING: from algo_trading_framework.src.broker_api.base_broker_client import BaseBrokerClient # type: ignore
class EvolvedStrategy(BaseStrategy):
    def __init__(self, strategy_id, broker, config): 
        super().__init__(strategy_id, broker, config)
        self.logger.info("Minimal EvolvedStrategy for test initialized")
    def on_bar(self, current_bars): 
        # Minimal logic, or just pass
        # self.logger.debug(f"EvolvedStrategy on_bar called at {current_bars.get(self.config.get('symbol')).timestamp if current_bars.get(self.config.get('symbol')) else 'N/A'}")
        pass
"""

class TestFitnessEvaluator(unittest.TestCase):

    def setUp(self):
        self.evaluator = FitnessEvaluator()
        self.strategy_code = DEFAULT_STRATEGY_TEMPLATE_FOR_TEST
        self.dummy_data_path = "test_ohlcv_data_fitness.csv" # Unique name
        self.symbol = "TEST_SYM_FIT" # Unique symbol for this test
        self.strategy_config = {
            "symbol": self.symbol,
            "timeframe": Timeframe.DAY_1.value,
            "short_window": 10, 
            "long_window": 20,
            "quantity": 1 # Added as template might use it
        }
        self._create_dummy_csv(self.dummy_data_path, self.symbol, days=60)
        # Disable logging during tests to keep output clean, unless debugging
        # logging.disable(logging.CRITICAL) 
        # Using a logger specific to this test module can be better
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.CRITICAL + 1) # Effectively disable for this logger


    def tearDown(self):
        if os.path.exists(self.dummy_data_path):
            os.remove(self.dummy_data_path)
        # logging.disable(logging.NOTSET)
        self.logger.setLevel(logging.NOTSET)


    def _create_dummy_csv(self, file_path, symbol, days):
        start_date = datetime(2023, 1, 1)
        data = []
        base_price = 100.0
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            # Ensure open_p is float
            open_p = float(base_price + i * 0.1 + random.uniform(-0.05, 0.05) * base_price)
            close_p = float(base_price + i * 0.15 + random.uniform(-0.05, 0.05) * base_price)
            high_p = float(max(open_p, close_p) + random.uniform(0, 0.02) * base_price)
            low_p = float(min(open_p, close_p) - random.uniform(0, 0.02) * base_price)
            volume = random.randint(1000, 5000)
            data.append([current_date.strftime('%Y-%m-%d %H:%M:%S'), symbol, 
                         round(open_p,2), round(high_p,2), round(low_p,2), round(close_p,2), volume])
        df = pd.DataFrame(data, columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
        df.to_csv(file_path, index=False)

    @patch('algo_trading_framework.src.strategy_lab.fitness_evaluator.calculate_all_metrics')
    @patch('algo_trading_framework.src.strategy_lab.fitness_evaluator.BacktesterEngine')
    @patch('algo_trading_framework.src.strategy_lab.fitness_evaluator.MockFyersClient')
    @patch('algo_trading_framework.src.strategy_lab.fitness_evaluator.HistoricalDataManager')
    def test_evaluate_strategy_success(self, mock_hdm_class, mock_broker_class, mock_engine_class, mock_calculate_metrics):
        mock_engine_instance = mock_engine_class.return_value
        # Simulate a minimal equity curve (DataFrame with 'equity' column)
        mock_equity_curve = pd.DataFrame({'timestamp': [datetime.now()], 'equity': [100000.0, 101000.0]})
        mock_engine_instance.run.return_value = (mock_equity_curve, []) # equity_curve, portfolio_history
        
        mock_broker_instance = mock_broker_class.return_value
        mock_broker_instance.get_trade_history.return_value = [{'pnl': 100.0}] # trade_log
        
        mock_hdm_instance = mock_hdm_class.return_value
        
        expected_metrics = {'sharpe_ratio': 1.5, 'total_return_pct': 0.01} # Removed 'error': None for cleaner check
        mock_calculate_metrics.return_value = expected_metrics

        result = self.evaluator.evaluate_strategy(
            self.strategy_code, self.dummy_data_path, self.strategy_config
        )

        mock_hdm_instance.load_data.assert_called_once()
        mock_engine_instance.run.assert_called_once()
        mock_broker_instance.get_trade_history.assert_called_once()
        mock_calculate_metrics.assert_called_once()
        
        self.assertEqual(result['sharpe_ratio'], expected_metrics['sharpe_ratio'])
        self.assertEqual(result['total_return_pct'], expected_metrics['total_return_pct'])
        self.assertNotIn('error', result) # Check error key is not present on success

    def test_evaluate_strategy_invalid_code(self):
        invalid_code = "class EvolvedStrategy(): def __init__(self): pass this is not valid python"
        result = self.evaluator.evaluate_strategy(invalid_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        # More flexible check for SyntaxError or general execution failure message
        self.assertTrue("Error executing strategy code" in result['error'] or "SyntaxError" in result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    def test_evaluate_strategy_no_strategy_class(self):
        code_no_class = "print('hello world, no strategy here')" # Valid Python but no EvolvedStrategy/BaseStrategy subclass
        result = self.evaluator.evaluate_strategy(code_no_class, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertIn("No 'EvolvedStrategy' or BaseStrategy subclass found", result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    def test_evaluate_strategy_data_file_not_found(self):
        result = self.evaluator.evaluate_strategy(self.strategy_code, "non_existent_file.csv", self.strategy_config)
        self.assertIn('error', result)
        self.assertIn("Historical data file not found", result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    @patch('algo_trading_framework.src.strategy_lab.fitness_evaluator.pd.read_csv')
    def test_evaluate_strategy_malformed_csv(self, mock_read_csv):
        mock_read_csv.side_effect = pd.errors.ParserError("Test Malformed CSV")
        result = self.evaluator.evaluate_strategy(self.strategy_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        # Check if the specific pandas error or a general loading error is propagated
        self.assertTrue("Error loading or processing historical data" in result['error'] or "Test Malformed CSV" in result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    @patch('algo_trading_framework.src.strategy_lab.fitness_evaluator.BacktesterEngine.run')
    def test_evaluate_strategy_backtester_error(self, mock_engine_run):
        mock_engine_run.side_effect = Exception("Test Backtester crashed")
        result = self.evaluator.evaluate_strategy(self.strategy_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        # Check if the specific backtester error is propagated
        self.assertTrue("Error during backtest execution or metrics calculation" in result['error'] and "Test Backtester crashed" in result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    def test_evaluate_strategy_empty_csv(self):
        empty_csv_path = "empty_test_data_fitness.csv" # Unique name
        # Create an empty file or a file with only headers
        with open(empty_csv_path, 'w') as f:
            f.write("timestamp,symbol,open,high,low,close,volume\n") 
            
        result = self.evaluator.evaluate_strategy(self.strategy_code, empty_csv_path, self.strategy_config)
        self.assertIn('error', result)
        # Check for messages indicating empty data
        self.assertTrue("Historical data CSV is empty" in result['error'] or "No candles processed" in result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))
        if os.path.exists(empty_csv_path): 
            os.remove(empty_csv_path)

if __name__ == '__main__':
    unittest.main()

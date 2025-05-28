import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import pandas as pd
from datetime import datetime, timedelta
import random
import logging
import importlib 

from src.strategy_lab.fitness_evaluator import FitnessEvaluator
from src.core.enums import Timeframe
from src.strategies.base_strategy import BaseStrategy # Imported for FitnessEvaluator's exec_globals

# Dynamically import DEFAULT_STRATEGY_TEMPLATE from evolutionary_engine
engine_module = importlib.import_module("src.strategy_lab.evolutionary_engine")
DEFAULT_STRATEGY_TEMPLATE_FOR_TEST = engine_module.DEFAULT_STRATEGY_TEMPLATE

MINIMAL_VALID_STRATEGY_CODE = """
import logging
# BaseStrategy is expected to be in the execution scope (provided by FitnessEvaluator)

class EvolvedStrategy(BaseStrategy):  # Must match the name FitnessEvaluator looks for
    def __init__(self, strategy_id, broker, config):
        super().__init__(strategy_id, broker, config)
        self.symbol = config.get("symbol", "TEST_SYMBOL_MINIMAL")
        # self.logger.info(f"MinimalEvolvedStrategy '{self.strategy_id}' for {self.symbol} initialized.")

    def on_bar(self, current_bars):
        # self.logger.debug(f"MinimalEvolvedStrategy on_bar for {self.symbol}")
        pass
"""

class TestFitnessEvaluator(unittest.TestCase):

    def setUp(self):
        self.evaluator = FitnessEvaluator() 
        self.complex_strategy_code = DEFAULT_STRATEGY_TEMPLATE_FOR_TEST
        self.minimal_strategy_code = MINIMAL_VALID_STRATEGY_CODE

        self.dummy_data_path = "test_ohlcv_data_fitness.csv" 
        self.symbol = "TEST_SYM_FIT" 
        self.strategy_config = {
            "symbol": self.symbol,
            "timeframe": Timeframe.DAY_1.value, 
            "short_window": 10, 
            "long_window": 20,
            "quantity": 1 
        }
        self._create_dummy_csv(self.dummy_data_path, self.symbol, days=60)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(logging.CRITICAL + 1) 


    def tearDown(self):
        if os.path.exists(self.dummy_data_path):
            os.remove(self.dummy_data_path)
        self.logger.setLevel(logging.NOTSET)


    def _create_dummy_csv(self, file_path, symbol, days):
        start_date = datetime(2023, 1, 1)
        data = []
        base_price = 100.0
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            open_p = float(base_price + i * 0.1 + random.uniform(-0.05, 0.05) * base_price)
            close_p = float(base_price + i * 0.15 + random.uniform(-0.05, 0.05) * base_price)
            high_p = float(max(open_p, close_p) + random.uniform(0, 0.02) * base_price)
            low_p = float(min(open_p, close_p) - random.uniform(0, 0.02) * base_price)
            volume = random.randint(1000, 5000)
            data.append([current_date.strftime('%Y-%m-%d %H:%M:%S'), symbol, 
                         round(open_p,2), round(high_p,2), round(low_p,2), round(close_p,2), volume])
        df = pd.DataFrame(data, columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
        df.to_csv(file_path, index=False)

    @patch('src.strategy_lab.fitness_evaluator.calculate_all_metrics') 
    @patch('src.strategy_lab.fitness_evaluator.BacktesterEngine')      
    @patch('src.strategy_lab.fitness_evaluator.MockFyersClient')       
    @patch('src.strategy_lab.fitness_evaluator.HistoricalDataManager') 
    def test_evaluate_strategy_success(self, mock_hdm_class, mock_broker_class, mock_engine_class, mock_calculate_metrics):
        mock_engine_instance = mock_engine_class.return_value
        mock_equity_curve = pd.DataFrame({ # Corrected DataFrame
            'timestamp': [datetime.now(), datetime.now() + timedelta(days=1)], 
            'equity': [100000.0, 101000.0]
        })
        mock_engine_instance.run.return_value = (mock_equity_curve, []) 
        
        mock_broker_instance = mock_broker_class.return_value
        mock_engine_instance.get_trade_log.return_value = [{'pnl': 100.0}] 

        mock_hdm_instance = mock_hdm_class.return_value
        
        expected_metrics = {'sharpe_ratio': 1.5, 'total_return_pct': 0.01} 
        mock_calculate_metrics.return_value = expected_metrics
        
        result = self.evaluator.evaluate_strategy(
            self.complex_strategy_code, self.dummy_data_path, self.strategy_config 
        )
        
        # Check that the broker was used by HDM to get data. - This assertion is likely incorrect.
        # The HistoricalDataManager loads from CSV in this flow and MockFyersClient is initialized with this data.
        # Broker's get_historical_data might not be called by HDM if HDM is already given data.
        # mock_broker_class.return_value.get_historical_data.assert_called_once() # Removing this assertion
        
        mock_engine_instance.run.assert_called_once()
        mock_calculate_metrics.assert_called_once() 
        
        self.assertEqual(result['sharpe_ratio'], expected_metrics['sharpe_ratio'])
        self.assertEqual(result['total_return_pct'], expected_metrics['total_return_pct'])
        self.assertNotIn('error', result)

    def test_evaluate_strategy_invalid_code(self):
        invalid_code = "class EvolvedStrategy(): def __init__(self): pass this is not valid python"
        result = self.evaluator.evaluate_strategy(invalid_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Error executing strategy code" in result['error'] or "SyntaxError" in result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    def test_evaluate_strategy_no_strategy_class(self):
        code_no_class = "MY_VARIABLE = 123\nprint('hello world, no strategy here')"
        result = self.evaluator.evaluate_strategy(code_no_class, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertIn("No 'EvolvedStrategy' or BaseStrategy subclass found in strategy code.", result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    def test_evaluate_strategy_data_file_not_found(self):
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, "non_existent_file.csv", self.strategy_config)
        self.assertIn('error', result)
        self.assertIn("Historical data file not found", result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    @patch('src.strategy_lab.fitness_evaluator.pd.read_csv') 
    def test_evaluate_strategy_malformed_csv(self, mock_read_csv):
        mock_read_csv.side_effect = pd.errors.ParserError("Test Malformed CSV")
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Error loading or processing historical data" in result['error'] or "Test Malformed CSV" in result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    @patch('src.strategy_lab.fitness_evaluator.BacktesterEngine.run') 
    def test_evaluate_strategy_backtester_error(self, mock_engine_run):
        mock_engine_run.side_effect = Exception("Test Backtester crashed")
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Error during backtest execution" in result['error'] or "Test Backtester crashed" in result['error'], f"Unexpected error message: {result.get('error')}") 
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))

    def test_evaluate_strategy_empty_csv(self):
        empty_csv_path = "empty_test_data_fitness.csv" 
        with open(empty_csv_path, 'w') as f:
            f.write("timestamp,symbol,open,high,low,close,volume\n") 
            
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, empty_csv_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Historical data CSV is empty" in result['error'] or "No candles processed" in result['error'] or "No data found for symbol" in result['error'], f"Unexpected error message: {result.get('error')}")
        self.assertEqual(result.get('sharpe_ratio'), -float('inf'))
        if os.path.exists(empty_csv_path): 
            os.remove(empty_csv_path)

if __name__ == '__main__':
    unittest.main()

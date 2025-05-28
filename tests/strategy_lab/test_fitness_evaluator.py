import unittest
from unittest.mock import patch, MagicMock, ANY # Added ANY
import os
import pandas as pd
from datetime import datetime, timedelta
import random
import logging
import importlib 

from src.strategy_lab.fitness_evaluator import FitnessEvaluator
from src.core.enums import Timeframe
from src.strategies.base_strategy import BaseStrategy 

engine_module = importlib.import_module("src.strategy_lab.evolutionary_engine")
DEFAULT_STRATEGY_TEMPLATE_FOR_TEST = engine_module.DEFAULT_STRATEGY_TEMPLATE

MINIMAL_VALID_STRATEGY_CODE = """
import logging
class EvolvedStrategy(BaseStrategy):
    def __init__(self, strategy_id, broker, config):
        super().__init__(strategy_id, broker, config)
        self.symbol = config.get("symbol", "TEST_SYMBOL_MINIMAL")
    def on_bar(self, current_bars):
        pass
"""

class TestFitnessEvaluator(unittest.TestCase):

    def setUp(self):
        self.evaluator = FitnessEvaluator(config={}) # Ensure config is passed
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

        # Sample data for engine run and trade history, used in the success test
        self.mock_portfolio_history = [
            {'timestamp': pd.Timestamp('2023-01-01'), 'total_value': 100000},
            {'timestamp': pd.Timestamp('2023-01-01'), 'total_value': 100500}, # Duplicate timestamp
            {'timestamp': pd.Timestamp('2023-01-02'), 'total_value': 101000}
        ]
        self.mock_equity_curve_values = [entry['total_value'] for entry in self.mock_portfolio_history] 
        
        self.mock_trade_log = [
            {'pnl': 100.0, 'symbol': 'TEST_SYM_FIT', 'timestamp': pd.Timestamp('2023-01-02 10:00:00'), 
             'side': 'BUY', 'quantity': 10, 'price': 100.0, 'commission': 1.0},
            {'pnl': 50.0, 'symbol': 'TEST_SYM_FIT', 'timestamp': pd.Timestamp('2023-01-03 10:00:00'), 
             'side': 'SELL', 'quantity': 5, 'price': 101.0, 'commission': 0.5}
        ]
        
        self.expected_metrics_from_reporter = {
            "Total Return [%]": 1.0, "CAGR [%]": 1.0, "Sharpe Ratio": 1.5, 
            "Sortino Ratio": 2.0, "Max Drawdown [%]": 5.0, "Calmar Ratio": 0.5,
            "Total Trades": 2, "Win Rate [%]": 100.0, "Profit Factor": float('inf'), 
            "Avg Winning Trade PnL": 75.0, "Avg Losing Trade PnL": 0.0,
        }


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

    @patch('src.strategy_lab.fitness_evaluator.pd.read_csv')
    @patch('src.strategy_lab.fitness_evaluator.BacktesterEngine')      
    @patch('src.strategy_lab.fitness_evaluator.MockFyersClient')       
    @patch('src.strategy_lab.fitness_evaluator.HistoricalDataManager') 
    @patch('src.strategy_lab.fitness_evaluator.PerformanceReporter') # Added patch for PerformanceReporter
    def test_evaluate_strategy_success_with_performance_reporter(self, 
                                                                 mock_performance_reporter_class, # Correct order
                                                                 mock_hdm_class, 
                                                                 mock_broker_class, 
                                                                 mock_engine_class, 
                                                                 mock_read_csv):
        # Setup mocks for file reading and backtesting components
        mock_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']), 
            'open': [100,100,100], 'high': [101,101,101], 'low': [99,99,99], 
            'close': [100,100,100], 'volume': [1000,1000,1000]
        })
        mock_read_csv.return_value = mock_df
        
        mock_engine_instance = mock_engine_class.return_value
        # engine.run() returns (raw_equity_values, portfolio_history)
        mock_engine_instance.run.return_value = (self.mock_equity_curve_values, self.mock_portfolio_history) 
        
        mock_broker_instance = mock_broker_class.return_value
        mock_broker_instance.get_trade_history.return_value = self.mock_trade_log

        # Setup PerformanceReporter mock
        mock_reporter_instance = mock_performance_reporter_class.return_value
        mock_reporter_instance.calculate_key_metrics.return_value = self.expected_metrics_from_reporter
        
        # Execute
        result = self.evaluator.evaluate_strategy(
            self.complex_strategy_code, self.dummy_data_path, self.strategy_config 
        )
        

        mock_performance_reporter_class.assert_called_once()
        call_args = mock_performance_reporter_class.call_args
        
        trades_df_arg = call_args.kwargs.get('trades')
        self.assertIsInstance(trades_df_arg, pd.DataFrame)
        self.assertEqual(len(trades_df_arg), len(self.mock_trade_log))
        self.assertEqual(trades_df_arg.iloc[0]['pnl'], self.mock_trade_log[0]['pnl'])

        equity_series_arg = call_args.kwargs.get('equity_curve')
        self.assertIsInstance(equity_series_arg, pd.Series)
        # Check length after duplicate handling (2 unique timestamps: 2023-01-01, 2023-01-02)
        self.assertEqual(len(equity_series_arg), 2) 
        self.assertEqual(equity_series_arg.loc[pd.Timestamp('2023-01-01')], 100500) # Last value for duplicate
        self.assertEqual(equity_series_arg.loc[pd.Timestamp('2023-01-02')], 101000)
        self.assertTrue(equity_series_arg.index.is_monotonic_increasing)

        mock_reporter_instance.calculate_key_metrics.assert_called_once()
        
        # Verify that the results from evaluate_strategy match what mock_calculate_key_metrics returned
        for key, expected_value in self.expected_metrics_from_reporter.items():
            self.assertEqual(result.get(key), expected_value, f"Metric '{key}' did not match. Got {result.get(key)}, expected {expected_value}")
        self.assertNotIn('error', result) # Assuming successful run means no 'error' field or it's None/benign.
                                         # FitnessEvaluator logic merges defaults, so error field might exist if not popped.
                                         # Current FE code: final_metrics.pop("error", None)
        
        # Check if BacktesterEngine was called with generate_analytics_report=False
        engine_call_args = mock_engine_class.call_args
        self.assertFalse(engine_call_args.kwargs.get('generate_analytics_report', True))


    # --- Tests for _convert_trades_to_dataframe ---
    def test_convert_trades_to_dataframe_empty(self):
        df = self.evaluator._convert_trades_to_dataframe([])
        self.assertTrue(df.empty)

    def test_convert_trades_to_dataframe_normal_data(self):
        trades = [
            {'symbol': 'AAPL', 'side': 'BUY', 'quantity': 10, 'price': 150.0, 'timestamp': '2023-01-01 10:00:00', 'pnl': 50.0, 'commission': 5.0},
            {'symbol': 'GOOG', 'side': 'SELL', 'quantity': 5, 'price': 2500.0, 'timestamp': '2023-01-02 11:00:00', 'pnl': -20.0, 'commission': 10.0}
        ]
        df = self.evaluator._convert_trades_to_dataframe(trades)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.loc[0, 'symbol'], 'AAPL')
        self.assertEqual(df.loc[1, 'pnl'], -20.0)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['timestamp']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['pnl']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['commission']))

    def test_convert_trades_to_dataframe_missing_columns(self):
        trades = [
            {'symbol': 'AAPL', 'side': 'BUY', 'quantity': 10, 'price': 150.0, 'timestamp': '2023-01-01 10:00:00'}, # Missing pnl, commission
        ]
        df = self.evaluator._convert_trades_to_dataframe(trades)
        self.assertEqual(df.loc[0, 'pnl'], 0.0) # Should default to 0.0
        self.assertTrue('commission' in df.columns) # Should be added
        self.assertEqual(df.loc[0, 'commission'], 0.0) # Should default to 0.0 if added by _convert_trades

    def test_convert_trades_to_dataframe_mixed_types_and_nan(self):
        trades = [
            {'symbol': 'A', 'side': 'BUY', 'quantity': '10', 'price': '150.0', 'timestamp': '2023-01-01', 'pnl': '50.0'},
            {'symbol': 'B', 'side': 'SELL', 'quantity': 5, 'price': None, 'timestamp': pd.NaT, 'pnl': -20.0, 'commission': 'abc'}
        ]
        df = self.evaluator._convert_trades_to_dataframe(trades)
        self.assertEqual(df.loc[0, 'quantity'], 10)
        self.assertEqual(df.loc[0, 'price'], 150.0)
        self.assertEqual(df.loc[0, 'pnl'], 50.0)
        self.assertTrue(pd.isna(df.loc[1, 'timestamp'])) # Timestamp NaT
        self.assertEqual(df.loc[1, 'price'], 0.0)      # Price None -> 0.0 by fillna(0) after to_numeric
        self.assertEqual(df.loc[1, 'commission'], 0.0) # 'abc' -> NaN by coerce -> 0.0 by fillna(0)

    # --- Existing Error Case Tests (adjust assertions for new default_error_metrics keys if needed) ---
    def test_evaluate_strategy_invalid_code(self):
        invalid_code = "class EvolvedStrategy(): def __init__(self): pass this is not valid python"
        result = self.evaluator.evaluate_strategy(invalid_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Error executing strategy code" in result['error'] or "SyntaxError" in result['error'])
        self.assertEqual(result.get('Sharpe Ratio'), -float('inf')) # Check a key from new default_error_metrics

    def test_evaluate_strategy_no_strategy_class(self):
        code_no_class = "MY_VARIABLE = 123\nprint('hello world, no strategy here')"
        result = self.evaluator.evaluate_strategy(code_no_class, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertIn("No 'EvolvedStrategy' or BaseStrategy subclass found in strategy code.", result['error'])
        self.assertEqual(result.get('Total Trades'), 0) # Check a key from new default_error_metrics

    def test_evaluate_strategy_data_file_not_found(self):
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, "non_existent_file.csv", self.strategy_config)
        self.assertIn('error', result)
        self.assertIn("Historical data file not found", result['error'])
        self.assertEqual(result.get('Max Drawdown [%]'), float('inf')) # Check a key from new default_error_metrics

    @patch('src.strategy_lab.fitness_evaluator.pd.read_csv') 
    def test_evaluate_strategy_malformed_csv(self, mock_read_csv):
        mock_read_csv.side_effect = pd.errors.ParserError("Test Malformed CSV")
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Error loading or processing historical data" in result['error'] or "Test Malformed CSV" in result['error'])
        self.assertEqual(result.get('Profit Factor'), 0.0) # Check a key

    @patch('src.strategy_lab.fitness_evaluator.BacktesterEngine.run') 
    def test_evaluate_strategy_backtester_error(self, mock_engine_run):
        mock_engine_run.side_effect = Exception("Test Backtester crashed")
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, self.dummy_data_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Error during backtest execution" in result['error'] or "Test Backtester crashed" in result['error']) 
        self.assertEqual(result.get('Win Rate [%]'), 0.0) # Check a key

    def test_evaluate_strategy_empty_csv(self):
        empty_csv_path = "empty_test_data_fitness.csv" 
        with open(empty_csv_path, 'w') as f:
            f.write("timestamp,symbol,open,high,low,close,volume\n") 
            
        result = self.evaluator.evaluate_strategy(self.minimal_strategy_code, empty_csv_path, self.strategy_config)
        self.assertIn('error', result)
        self.assertTrue("Historical data CSV is empty" in result['error'] or "No candles processed" in result['error'] or "No data found for symbol" in result['error'])
        self.assertEqual(result.get('Total Return [%]'), -float('inf')) # Check a key
        if os.path.exists(empty_csv_path): 
            os.remove(empty_csv_path)

if __name__ == '__main__':
    unittest.main()
import unittest
from unittest.mock import patch, MagicMock, ANY
import pandas as pd
from datetime import datetime, timezone

from src.strategy_lab.fitness_evaluator import FitnessEvaluator
from src.strategies.base_strategy import BaseStrategy as ActualBaseStrategy # Alias to avoid confusion
from src.broker_api.mock_fyers_client import MockFyersClient as ActualMockFyersClient # For type hinting if needed
from src.backtester.engine import BacktesterEngine as ActualBacktesterEngine # For type hinting if needed
from src.analytics.performance_reporter import PerformanceReporter as ActualPerformanceReporter # For type hinting
from src.core.models import Candle, Trade # For type hinting if needed
from src.core.enums import OrderSide # For type hinting if needed

class TestFitnessEvaluator(unittest.TestCase):
    """
    Test suite for the FitnessEvaluator class.
    """

    def setUp(self):
        self.valid_strategy_code = """
from src.strategies.base_strategy import BaseStrategy

class EvolvedStrategy(BaseStrategy):
    def __init__(self, broker_client, config):
        super().__init__(broker_client, config)
        self.symbol = config.get('symbol', 'DEFAULT_SYMBOL')
        self.quantity = config.get('quantity', 1)

    def on_bar(self, current_bar_data: dict):
        # print(f"EvolvedStrategy on_bar: {current_bar_data}")
        pass
"""
        self.historical_data_path = "dummy_fitness_data.csv"
        self.strategy_config = {'symbol': 'SYM1', 'timeframe': '1D', 'quantity': 10}
        self.start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2023, 1, 10, tzinfo=timezone.utc)

        # Default evaluator
        self.evaluator = FitnessEvaluator(
            start_date=self.start_date,
            end_date=self.end_date,
            initial_cash=100000,
            commission_per_trade=0.01,
            slippage_percent=0.001
        )
    
    @patch('src.strategy_lab.fitness_evaluator.PerformanceReporter')
    @patch('src.strategy_lab.fitness_evaluator.BacktesterEngine')
    @patch('src.strategy_lab.fitness_evaluator.HistoricalDataManager') 
    @patch('src.strategy_lab.fitness_evaluator.MockFyersClient')
    @patch('pandas.read_csv')
    def test_successful_strategy_evaluation_flow(self, mock_read_csv, MockedBroker, 
                                                 MockedHDM, MockedEngine, MockedReporter):
        # 4.c. Mock pd.read_csv
        mock_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'open': [100, 101], 'high': [102, 103], 'low': [99, 100],
            'close': [101, 102], 'volume': [1000, 1000]
        })
        mock_read_csv.return_value = mock_df

        # 4.h. Configure MockedEngine
        MockedEngine.return_value.run.return_value = ([], []) # (raw_equity_values, engine_portfolio_history)

        # 4.i. Configure broker.portfolio_history for PerformanceReporter
        mock_broker_instance = MockedBroker.return_value 
        sample_broker_portfolio_history = [
            {'timestamp': datetime(2023,1,1, tzinfo=timezone.utc), 'total_value': 100000, 'cash': 100000, 'positions_market_value': 0},
            {'timestamp': datetime(2023,1,2, tzinfo=timezone.utc), 'total_value': 101000, 'cash': 90000, 'positions_market_value': 11000}
        ]
        # Make portfolio_history an attribute of the mock instance
        mock_broker_instance.portfolio_history = sample_broker_portfolio_history
        
        # 4.j. Configure get_trade_history
        mock_broker_instance.get_trade_history.return_value = []

        # 4.k. Configure MockedReporter
        # Using a more complete set of metrics as FitnessEvaluator selects specific ones
        mocked_metrics_output = {
            "Sharpe Ratio": 1.5, "Total Return [%]": 10.0, "Max Drawdown [%]": -5.0, 
            "Profit Factor": 2.0, "CAGR [%]": 12.0, "Win Rate [%]": 60.0, 
            "Total Trades": 10, "Avg Trade PnL": 100.0
        }
        MockedReporter.return_value.calculate_key_metrics.return_value = mocked_metrics_output

        # 4.l. Call evaluate_strategy
        result = self.evaluator.evaluate_strategy(
            self.valid_strategy_code, 
            self.historical_data_path, 
            self.strategy_config
        )

        # 4.m. Assert pd.read_csv
        mock_read_csv.assert_called_once_with(self.historical_data_path)

        # 4.n. Assert MockedEngine was instantiated
        MockedEngine.assert_called_once()
        engine_args, engine_kwargs = MockedEngine.call_args
        self.assertIsInstance(engine_kwargs['strategy'], ActualBaseStrategy) 
        self.assertIs(engine_kwargs['broker'], mock_broker_instance)
        self.assertIsInstance(engine_kwargs['historical_data_manager'], MockedHDM.return_value.__class__)
        self.assertEqual(engine_kwargs['symbols_to_trade'], [self.strategy_config['symbol']])
        self.assertEqual(engine_kwargs['timeframe'], self.strategy_config['timeframe'])


        # 4.o. Assert MockedEngine.return_value.run was called
        MockedEngine.return_value.run.assert_called_once()

        # 4.p. Assert MockedBroker.return_value.get_trade_history was called
        mock_broker_instance.get_trade_history.assert_called_once()

        # 4.q. Assert MockedReporter was instantiated
        MockedReporter.assert_called_once()
        reporter_args, reporter_kwargs = MockedReporter.call_args
        
        expected_equity_series = pd.Series(
            [d['total_value'] for d in sample_broker_portfolio_history], 
            index=pd.to_datetime([d['timestamp'] for d in sample_broker_portfolio_history])
        )
        pd.testing.assert_series_equal(reporter_kwargs['equity_curve_series'], expected_equity_series, check_names=False)
        
        self.assertIsInstance(reporter_kwargs['trades_df'], pd.DataFrame)
        self.assertTrue(reporter_kwargs['trades_df'].empty)


        # 4.r. Assert MockedReporter.return_value.calculate_key_metrics was called
        MockedReporter.return_value.calculate_key_metrics.assert_called_once()

        # 4.s. Assert the result
        # FitnessEvaluator selects specific keys from the reporter's output
        expected_result = {
            "Total Return [%]": 10.0, "Sharpe Ratio": 1.5, "Max Drawdown [%]": -5.0,
            "Profit Factor": 2.0, "CAGR [%]": 12.0, "error": None # error is None on success
        }
        self.assertEqual(result, expected_result)


    def test_strategy_code_execution_error(self):
        # 5.a. Provide strategy_code_string
        invalid_code = "raise SyntaxError('test syntax error')"
        
        # 5.b. Call evaluate_strategy
        result = self.evaluator.evaluate_strategy(
            invalid_code, 
            self.historical_data_path, 
            self.strategy_config
        )
        
        # 5.c. Assert error key
        self.assertIn('error', result)
        self.assertIsNotNone(result['error'])
        self.assertIn("Error executing strategy code: SyntaxError('test syntax error')", result['error'])
        # Check default fitness values for error case
        self.assertEqual(result["Total Return [%]"], -100.0) 
        self.assertEqual(result["Sharpe Ratio"], -10.0)
        self.assertEqual(result["Max Drawdown [%]"], -100.0)
        self.assertEqual(result["Profit Factor"], 0.0)
        self.assertEqual(result["CAGR [%]"], -100.0)


    @patch('pandas.read_csv')
    def test_historical_data_not_found(self, mock_read_csv):
        # 6.a. Mock pd.read_csv to raise FileNotFoundError
        mock_read_csv.side_effect = FileNotFoundError("File not found test error")
        
        # 6.c. Call evaluate_strategy
        result = self.evaluator.evaluate_strategy(
            self.valid_strategy_code, 
            "non_existent_path.csv", 
            self.strategy_config
        )
        
        # 6.d. Assert error key
        self.assertIn('error', result)
        self.assertIsNotNone(result['error'])
        self.assertIn("Error loading historical data: File not found test error", result['error'])
        self.assertEqual(result["Total Return [%]"], -100.0) 
        self.assertEqual(result["Sharpe Ratio"], -10.0)
        self.assertEqual(result["Max Drawdown [%]"], -100.0)
        self.assertEqual(result["Profit Factor"], 0.0)
        self.assertEqual(result["CAGR [%]"], -100.0)


if __name__ == '__main__':
    unittest.main()

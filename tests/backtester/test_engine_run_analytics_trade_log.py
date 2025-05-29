import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pandas as pd

from src.backtester.engine import BacktesterEngine
from src.strategies.base_strategy import BaseStrategy
from src.broker_api.base_broker_client import BaseBrokerClient
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.core.models import Trade # Trade model for potential type hints if sample_trades were Trade objects
from src.core.enums import OrderSide

class TestBacktesterEngineRunAnalyticsTradeLog(unittest.TestCase):
    """
    Test suite for verifying BacktesterEngine's interaction with the broker's 
    trade log when generate_analytics_report is true.
    """

    def setUp(self):
        """
        Set up mocks and a BacktesterEngine instance for each test.
        """
        self.mock_strategy = MagicMock(spec=BaseStrategy)
        self.mock_broker = MagicMock(spec=BaseBrokerClient)
        self.mock_hdm = MagicMock(spec=HistoricalDataManager)

        self.start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2023, 1, 5, tzinfo=timezone.utc)
        self.symbols = ["SYM1"]
        self.timeframe = "1D"

        self.engine = BacktesterEngine(
            strategy=self.mock_strategy,
            broker=self.mock_broker,
            historical_data_manager=self.mock_hdm,
            symbols_to_trade=self.symbols,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            generate_analytics_report=True # Crucial for this test
        )
        # Mock initial cash sync
        self.mock_broker.cash = 100000.0

    # Test Case 1: Engine Fetches and Uses Trade Log for Analytics
    @patch('src.backtester.engine.PerformanceReporter') # Mock PerformanceReporter
    def test_engine_fetches_and_uses_trade_log_for_analytics(self, MockPerformanceReporter):
        # 5.a. Configure HDM mock for empty data
        self.mock_hdm.get_all_data_sorted_by_timestamp.return_value = []
        
        # 5.b. Define a sample trade log
        # Using timezone-aware datetimes
        ts1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2023, 1, 2, 11, 0, tzinfo=timezone.utc)
        sample_trades_list_of_dicts = [
            {'trade_id': 't1', 'order_id': 'o1', 'symbol': 'SYM1', 'quantity': 10, 'price': 100.0, 'side': OrderSide.BUY, 'timestamp': ts1, 'commission': 1.0, 'pnl': 0.0},
            {'trade_id': 't2', 'order_id': 'o2', 'symbol': 'SYM1', 'quantity': 10, 'price': 105.0, 'side': OrderSide.SELL, 'timestamp': ts2, 'commission': 1.0, 'pnl': 50.0}
        ]
        # If MockFyersClient.get_trade_history returns Trade objects, this would be:
        # sample_trades_objects = [
        #     Trade(trade_id='t1', order_id='o1', symbol='SYM1', quantity=10, price=100.0, side=OrderSide.BUY, timestamp=ts1, commission=1.0, pnl=0.0),
        #     Trade(trade_id='t2', order_id='o2', symbol='SYM1', quantity=10, price=105.0, side=OrderSide.SELL, timestamp=ts2, commission=1.0, pnl=50.0)
        # ]
        # Assuming get_trade_history returns a list of dicts as per the problem description.

        # 5.c. Configure broker.get_trade_history
        self.mock_broker.get_trade_history.return_value = sample_trades_list_of_dicts
        
        # 5.d. Configure broker.get_balance
        self.mock_broker.get_balance.return_value = {'cash': 100000.0, 'margin_available': 100000.0, 'margin_used': 0.0}
        # 5.e. Configure broker.get_positions
        self.mock_broker.get_positions.return_value = []

        # Mock instance of PerformanceReporter to check its methods
        mock_reporter_instance = MockPerformanceReporter.return_value
        mock_reporter_instance.generate_report.return_value = ("summary_html", "plot_html") # Mock its return

        # 5.g. Call self.engine.run()
        self.engine.run()

        # 5.h. Assert broker.get_trade_history was called once
        self.mock_broker.get_trade_history.assert_called_once()

        # 5.i. Access arguments passed to PerformanceReporter constructor
        # PerformanceReporter is instantiated with (portfolio_history_df, trades_df)
        # We need to check the trades_df passed to it.
        # The engine calls _convert_trades_to_dataframe internally.
        # The actual call to PerformanceReporter is inside engine.run() after the loop.
        
        # Check that PerformanceReporter was instantiated
        MockPerformanceReporter.assert_called_once()
        
        # Get the arguments passed to the constructor of PerformanceReporter
        # The first positional argument is portfolio_history_df, the second is trades_df
        constructor_args, _ = MockPerformanceReporter.call_args
        
        # The trades DataFrame is the second argument to PerformanceReporter
        trades_df_passed_to_reporter = constructor_args[1] 
        
        self.assertIsInstance(trades_df_passed_to_reporter, pd.DataFrame)
        
        # Verify number of rows
        self.assertEqual(len(trades_df_passed_to_reporter), len(sample_trades_list_of_dicts))
        
        # Verify some key values and timestamp conversion
        self.assertEqual(trades_df_passed_to_reporter['trade_id'].iloc[0], sample_trades_list_of_dicts[0]['trade_id'])
        self.assertEqual(trades_df_passed_to_reporter['symbol'].iloc[1], sample_trades_list_of_dicts[1]['symbol'])
        self.assertEqual(trades_df_passed_to_reporter['price'].iloc[0], sample_trades_list_of_dicts[0]['price'])
        self.assertEqual(trades_df_passed_to_reporter['side'].iloc[1], sample_trades_list_of_dicts[1]['side']) # Should be OrderSide.SELL
        
        # Verify 'timestamp' column is datetime
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(trades_df_passed_to_reporter['timestamp']))
        # Compare actual datetime objects, ensuring they are timezone-aware if original ones are
        self.assertEqual(trades_df_passed_to_reporter['timestamp'].iloc[0].to_pydatetime(), ts1)
        self.assertEqual(trades_df_passed_to_reporter['timestamp'].iloc[1].to_pydatetime(), ts2)

        # Verify that the generate_report method of the reporter instance was called
        mock_reporter_instance.generate_report.assert_called_once()

if __name__ == '__main__':
    unittest.main()

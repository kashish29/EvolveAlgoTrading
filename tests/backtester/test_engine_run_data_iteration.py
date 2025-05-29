import unittest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone

from src.backtester.engine import BacktesterEngine
from src.strategies.base_strategy import BaseStrategy
from src.broker_api.base_broker_client import BaseBrokerClient
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.core.models import Candle

class TestBacktesterEngineRunDataIteration(unittest.TestCase):
    """
    Test suite for the data iteration logic within the run() method of BacktesterEngine.
    """

    def setUp(self):
        """
        Set up mocks and a BacktesterEngine instance for each test.
        """
        self.mock_strategy = MagicMock(spec=BaseStrategy)
        self.mock_broker = MagicMock(spec=BaseBrokerClient)
        self.mock_broker.logger = MagicMock() 
        self.mock_broker.set_current_bar = MagicMock()
        self.mock_broker._process_pending_orders = MagicMock() # Add _process_pending_orders
        self.mock_hdm = MagicMock(spec=HistoricalDataManager)

        self.start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2023, 1, 3, tzinfo=timezone.utc) # Adjusted to cover test data
        self.symbols = ["SYM1"]
        self.timeframe = "1D"

        self.engine = BacktesterEngine(
            strategy=self.mock_strategy,
            broker=self.mock_broker,
            historical_data_manager=self.mock_hdm,
            symbols=self.symbols, # Changed from symbols_to_trade
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            generate_analytics_report=False # Keep analytics off for these tests
        )

    # Test Case 1: Data Iteration and Method Calls
    def test_data_iteration_and_method_calls(self):
        # 5.a. Prepare a small mock dataset
        ts1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2023, 1, 2, 10, 0, tzinfo=timezone.utc)
        
        candle1_sym1 = Candle(timestamp=ts1, symbol="SYM1", open=100, high=101, low=99, close=100, volume=1000)
        candle2_sym1 = Candle(timestamp=ts2, symbol="SYM1", open=101, high=102, low=100, close=101, volume=1200)
        
        mock_market_data = [
            (ts1, {"SYM1": candle1_sym1}),
            (ts2, {"SYM1": candle2_sym1})
        ]

        # 5.b. Configure HDM mock
        self.mock_hdm.get_all_data_sorted_by_timestamp.return_value = mock_market_data
        
        # 5.c. Configure broker mocks for portfolio calculation
        self.mock_broker.get_balance.return_value = {'cash': 100000.0, 'margin_available': 100000.0, 'margin_used': 0.0}
        # 5.d.
        self.mock_broker.get_positions.return_value = [] 
        # Mock initial cash for broker, so engine can sync it
        self.mock_broker.cash = 100000.0 


        # 5.e. Call self.engine.run()
        self.engine.run()

        # 5.f. Assert HDM call
        self.mock_hdm.get_all_data_sorted_by_timestamp.assert_called_once_with(
            symbols=self.symbols, timeframe=self.timeframe, start_date=self.start_date, end_date=self.end_date
        )

        # current_time is an attribute on the broker, set by the engine.
        # We can check its final value after the loop if needed, or trust it's set.
        # Removing method call assertions for 'set_current_time'.
        # Check final value:
        self.assertEqual(self.mock_broker.current_time, ts2)


        # 5.h. Assert broker.set_current_bar calls
        set_current_bar_calls = [
            call("SYM1", candle1_sym1),
            call("SYM1", candle2_sym1)
        ]
        # Note: set_current_bar is called within a loop for each symbol in the current bar's data.
        # So, for each timestamp, it's called once for "SYM1".
        self.mock_broker.set_current_bar.assert_has_calls(set_current_bar_calls)
        self.assertEqual(self.mock_broker.set_current_bar.call_count, 2)


        # 5.i. Assert strategy.on_bar calls
        on_bar_calls = [
            call({"SYM1": candle1_sym1}),
            call({"SYM1": candle2_sym1})
        ]
        self.mock_strategy.on_bar.assert_has_calls(on_bar_calls)
        self.assertEqual(self.mock_strategy.on_bar.call_count, 2)

        # 5.j. (Optional) Assert broker._process_pending_orders calls
        # This method is protected, but if its effect is important, test that.
        # Assuming it's called after strategy.on_bar for each timestamp.
        self.assertEqual(self.mock_broker._process_pending_orders.call_count, 2)
        
        # get_balance is called inside the loop for each timestamp.
        self.assertEqual(self.mock_broker.get_balance.call_count, len(mock_market_data))


    # Test Case 2: Empty Market Data
    def test_empty_market_data(self):
        # 6.a. Configure HDM mock to return empty list
        self.mock_hdm.get_all_data_sorted_by_timestamp.return_value = []
        
        # Configure broker mocks for initial state
        self.mock_broker.get_balance.return_value = {'cash': 100000.0, 'margin_available': 100000.0, 'margin_used': 0.0}
        self.mock_broker.get_positions.return_value = []
        self.mock_broker.cash = 100000.0


        # 6.b. Call self.engine.run()
        equity_curve, portfolio_history = self.engine.run()

        # 6.c. Assert strategy.on_bar was NOT called
        self.mock_strategy.on_bar.assert_not_called()
        
        # current_time is an attribute, not a method. If loop isn't entered, it won't be set by engine.
        # No direct mock assertion needed for current_time not being set unless specifically checking its final state.
        
        # Assert broker.set_current_bar was NOT called
        self.mock_broker.set_current_bar.assert_not_called()

        # Assert broker._process_pending_orders was NOT called
        self.mock_broker._process_pending_orders.assert_not_called()

        # 6.e. Assert that the run method returns ([], [])
        self.assertEqual(equity_curve, [], "Equity curve should be empty for no market data.")
        self.assertEqual(portfolio_history, [], "Portfolio history should be empty for no market data.")
        
        # Initial portfolio update should still happen once if generate_analytics_report is True,
        # but here it's False. If it were true, one entry for initial state might be present.
        # Let's confirm the internal lists are also empty.
        self.assertEqual(self.engine.equity_curve, [])
        self.assertEqual(self.engine.portfolio_history, [])


if __name__ == '__main__':
    unittest.main()

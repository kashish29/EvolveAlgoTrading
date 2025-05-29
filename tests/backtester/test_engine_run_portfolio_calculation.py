import unittest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone

from src.backtester.engine import BacktesterEngine
from src.strategies.base_strategy import BaseStrategy
from src.broker_api.base_broker_client import BaseBrokerClient
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.core.models import Candle

class TestBacktesterEngineRunPortfolioCalculation(unittest.TestCase):
    """
    Test suite for the portfolio equity curve calculation logic 
    within the run() method of BacktesterEngine.
    """

    def setUp(self):
        """
        Set up mocks and a BacktesterEngine instance for each test.
        """
        self.mock_strategy = MagicMock(spec=BaseStrategy)
        self.mock_broker = MagicMock(spec=BaseBrokerClient)
        self.mock_hdm = MagicMock(spec=HistoricalDataManager)

        self.start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2023, 1, 5, tzinfo=timezone.utc) # Wide enough for tests
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
            generate_analytics_report=False 
        )
        # Mock initial cash sync
        self.mock_broker.cash = 100000.0 # Default for some tests

    # Test Case 1: Portfolio Calculation - Single Bar, No Positions
    def test_portfolio_calc_single_bar_no_positions(self):
        ts1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        candle1_sym1 = Candle(timestamp=ts1, symbol="SYM1", open=100, high=101, low=99, close=100, volume=1000)
        
        self.mock_hdm.get_all_data_sorted_by_timestamp.return_value = [(ts1, {"SYM1": candle1_sym1})]
        
        self.mock_broker.get_balance.return_value = {'cash': 100000.0, 'margin_available': 100000.0, 'margin_used': 0.0}
        self.mock_broker.get_positions.return_value = []
        self.mock_broker.cash = 100000.0 # Ensure engine syncs this cash value

        equity_curve, portfolio_history = self.engine.run()

        self.assertEqual(len(portfolio_history), 1)
        self.assertEqual(portfolio_history[0]['timestamp'], ts1)
        self.assertEqual(portfolio_history[0]['cash'], 100000.0)
        self.assertEqual(portfolio_history[0]['positions_market_value'], 0.0)
        self.assertEqual(portfolio_history[0]['total_value'], 100000.0)
        self.assertEqual(equity_curve, [100000.0])

    # Test Case 2: Portfolio Calculation - Single Bar, One Position
    def test_portfolio_calc_single_bar_one_position(self):
        ts1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        candle1_sym1 = Candle(timestamp=ts1, symbol="SYM1", open=100, high=101, low=99, close=100, volume=1000)

        self.mock_hdm.get_all_data_sorted_by_timestamp.return_value = [(ts1, {"SYM1": candle1_sym1})]
        
        self.mock_broker.get_balance.return_value = {'cash': 90000.0, 'margin_available': 90000.0, 'margin_used': 1000.0}
        self.mock_broker.get_positions.return_value = [{'symbol': 'SYM1', 'quantity': 10, 'average_price': 98.0, 'last_price': 100.0}]
        self.mock_broker.get_current_bar = MagicMock(return_value=candle1_sym1) # Simulate broker having current bar
        self.mock_broker.cash = 90000.0

        equity_curve, portfolio_history = self.engine.run()

        expected_positions_market_value = 10 * 100.0 # quantity * candle.close
        expected_total_value = 90000.0 + expected_positions_market_value

        self.assertEqual(len(portfolio_history), 1)
        self.assertEqual(portfolio_history[0]['timestamp'], ts1)
        self.assertEqual(portfolio_history[0]['cash'], 90000.0)
        self.assertEqual(portfolio_history[0]['positions_market_value'], expected_positions_market_value)
        self.assertEqual(portfolio_history[0]['total_value'], expected_total_value)
        self.assertEqual(equity_curve, [expected_total_value])

    # Test Case 3: Portfolio Calculation - Position Valuation Fallback (No Current Bar)
    def test_portfolio_calc_position_valuation_fallback(self):
        ts1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        # Candle is still provided to HDM to drive the loop, but broker won't have it via get_current_bar
        candle_for_hdm = Candle(timestamp=ts1, symbol="SYM1", open=100, high=101, low=99, close=100, volume=1000)
        self.mock_hdm.get_all_data_sorted_by_timestamp.return_value = [(ts1, {"SYM1": candle_for_hdm})]

        self.mock_broker.get_balance.return_value = {'cash': 90000.0, 'margin_available': 90000.0, 'margin_used': 1000.0}
        # Position data itself has 'last_price': 100.0
        position_with_last_price = [{'symbol': 'SYM1', 'quantity': 10, 'average_price': 98.0, 'last_price': 100.0}]
        self.mock_broker.get_positions.return_value = position_with_last_price
        self.mock_broker.get_current_bar = MagicMock(return_value=None) # Broker has no current bar for SYM1
        self.mock_broker.cash = 90000.0

        equity_curve, portfolio_history = self.engine.run()

        expected_positions_market_value = 10 * 100.0 # quantity * position's last_price
        expected_total_value = 90000.0 + expected_positions_market_value

        self.assertEqual(len(portfolio_history), 1)
        self.assertEqual(portfolio_history[0]['timestamp'], ts1)
        self.assertEqual(portfolio_history[0]['cash'], 90000.0)
        self.assertEqual(portfolio_history[0]['positions_market_value'], expected_positions_market_value)
        self.assertEqual(portfolio_history[0]['total_value'], expected_total_value)
        self.assertEqual(equity_curve, [expected_total_value])

    # Test Case 4: Two Bars, Position Value Change
    def test_portfolio_calc_two_bars_position_value_change(self):
        ts1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2023, 1, 2, 10, 0, tzinfo=timezone.utc)
        
        candle1 = Candle(timestamp=ts1, symbol="SYM1", open=100, high=101, low=99, close=100, volume=1000)
        candle2 = Candle(timestamp=ts2, symbol="SYM1", open=101, high=106, low=100, close=105, volume=1200)
        
        self.mock_hdm.get_all_data_sorted_by_timestamp.return_value = [
            (ts1, {"SYM1": candle1}),
            (ts2, {"SYM1": candle2})
        ]
        
        # Mock broker responses
        self.mock_broker.get_balance.return_value = {'cash': 90000.0, 'margin_available': 90000.0, 'margin_used': 1000.0}
        positions_data = [{'symbol': 'SYM1', 'quantity': 10, 'average_price': 98.0, 'last_price': 100.0}] # last_price might be updated by broker internally
        self.mock_broker.get_positions.return_value = positions_data
        
        # Simulate broker's get_current_bar updating for each bar
        def get_current_bar_side_effect(symbol):
            if self.mock_broker.current_time == ts1 and symbol == "SYM1":
                return candle1
            elif self.mock_broker.current_time == ts2 and symbol == "SYM1":
                return candle2
            return None
        self.mock_broker.get_current_bar = MagicMock(side_effect=get_current_bar_side_effect)
        self.mock_broker.cash = 90000.0

        equity_curve, portfolio_history = self.engine.run()

        self.assertEqual(len(portfolio_history), 2)

        # Bar 1
        mv1 = 10 * 100.0 # quantity * candle1.close
        tv1 = 90000.0 + mv1
        self.assertEqual(portfolio_history[0]['timestamp'], ts1)
        self.assertEqual(portfolio_history[0]['cash'], 90000.0)
        self.assertEqual(portfolio_history[0]['positions_market_value'], mv1)
        self.assertEqual(portfolio_history[0]['total_value'], tv1)

        # Bar 2
        mv2 = 10 * 105.0 # quantity * candle2.close
        tv2 = 90000.0 + mv2
        self.assertEqual(portfolio_history[1]['timestamp'], ts2)
        self.assertEqual(portfolio_history[1]['cash'], 90000.0) # Cash assumed constant for this test
        self.assertEqual(portfolio_history[1]['positions_market_value'], mv2)
        self.assertEqual(portfolio_history[1]['total_value'], tv2)
        
        self.assertEqual(equity_curve, [tv1, tv2])

if __name__ == '__main__':
    unittest.main()

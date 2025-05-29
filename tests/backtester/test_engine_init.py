import unittest
from unittest.mock import MagicMock
import datetime

from src.backtester.engine import BacktesterEngine
from src.strategies.base_strategy import BaseStrategy
from src.broker_api.base_broker_client import BaseBrokerClient
from src.data_handler.historical_data_manager import HistoricalDataManager

class TestBacktesterEngineInit(unittest.TestCase):
    """
    Test suite for the __init__() method of the BacktesterEngine class.
    """

    def test_engine_initialization_non_default_analytics(self):
        """
        Tests the BacktesterEngine initialization with generate_analytics_report set to False.
        """
        # 4.a. Create MagicMock instances
        mock_strategy = MagicMock(spec=BaseStrategy)
        mock_broker = MagicMock(spec=BaseBrokerClient)
        mock_hdm = MagicMock(spec=HistoricalDataManager)

        # 4.b. Define sample values
        symbols = ["SYM1", "SYM2"]
        timeframe = "1D"
        start_date = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2023, 1, 31, tzinfo=datetime.timezone.utc)
        generate_analytics_val = False

        # 4.c. Instantiate BacktesterEngine
        engine = BacktesterEngine(
            strategy=mock_strategy,
            broker=mock_broker,
            historical_data_manager=mock_hdm,
            symbols_to_trade=symbols,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            generate_analytics_report=generate_analytics_val
        )

        # 4.d. Assert that engine.strategy is mock_strategy
        self.assertIs(engine.strategy, mock_strategy)

        # 4.e. Assert that engine.broker is mock_broker
        self.assertIs(engine.broker, mock_broker)

        # 4.f. Assert that engine.historical_data_manager is mock_hdm
        self.assertIs(engine.historical_data_manager, mock_hdm)

        # 4.g. Assert that engine.symbols_to_trade is equal to symbols
        self.assertEqual(engine.symbols_to_trade, symbols)

        # 4.h. Assert that engine.timeframe is equal to timeframe
        self.assertEqual(engine.timeframe, timeframe)

        # 4.i. Assert that engine.start_date is equal to start_date
        self.assertEqual(engine.start_date, start_date)

        # 4.j. Assert that engine.end_date is equal to end_date
        self.assertEqual(engine.end_date, end_date)

        # 4.k. Assert that engine.generate_analytics_report is equal to generate_analytics_val
        self.assertEqual(engine.generate_analytics_report, generate_analytics_val)

        # 4.l. Assert that engine.equity_curve is an empty list
        self.assertEqual(engine.equity_curve, [])

        # 4.m. Assert that engine.portfolio_history is an empty list
        self.assertEqual(engine.portfolio_history, [])
        
        # Additional check for initial portfolio state
        self.assertEqual(engine.portfolio_value, 0.0)
        self.assertEqual(engine.current_cash, 0.0) # Assuming it's set later via broker
        self.assertEqual(engine.current_holdings, {})
        self.assertEqual(engine.trade_log, [])


    def test_engine_initialization_default_analytics(self):
        """
        Tests the BacktesterEngine initialization with generate_analytics_report using its default value (True).
        """
        mock_strategy = MagicMock(spec=BaseStrategy)
        mock_broker = MagicMock(spec=BaseBrokerClient)
        mock_hdm = MagicMock(spec=HistoricalDataManager)

        symbols = ["SYM1"]
        timeframe = "1H"
        start_date = datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2022, 1, 5, tzinfo=datetime.timezone.utc)

        # Instantiate BacktesterEngine without passing generate_analytics_report
        engine = BacktesterEngine(
            strategy=mock_strategy,
            broker=mock_broker,
            historical_data_manager=mock_hdm,
            symbols_to_trade=symbols,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
            # generate_analytics_report is omitted to use default
        )

        # Assert that engine.generate_analytics_report is True (the default)
        self.assertTrue(engine.generate_analytics_report)

if __name__ == '__main__':
    unittest.main()

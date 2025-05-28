import unittest
from unittest.mock import patch, MagicMock, call
import pandas as pd
import datetime
import logging

from src.backtester.engine import BacktesterEngine
from src.strategies.base_strategy import BaseStrategy
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.core.models import Candle # Assuming Timeframe enum is not strictly needed for these tests if timeframe is passed as string

# Minimal Dummy strategy for testing
class DummyStrategy(BaseStrategy):
    def __init__(self, strategy_id: str, broker, config: dict): # Adjusted to match typical BaseStrategy __init__
        super().__init__(strategy_id, broker, config)
        # Minimal implementation
    
    def on_bar(self, current_bar_data: dict): # Adjusted to match typical BaseStrategy on_bar
        pass # Does nothing for integration testing purposes

# Minimal Mock Broker for controlling trade history and portfolio updates
class MinimalMockBroker:
    def __init__(self, initial_cash=100000):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = {} # symbol: {'quantity': X, 'average_price': Y, 'last_price': Z}
        self.trade_history = []
        self.current_time = None
        self.logger = logging.getLogger("MinimalMockBroker") # Basic logger
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.hasHandlers(): # Avoid duplicate handlers if tests run multiple times
            self.logger.addHandler(logging.StreamHandler())


    def get_trade_history(self):
        return self.trade_history

    def get_balance(self):
        return {"cash": self.cash, "total_funds": self.cash + self._get_positions_value()}

    def get_positions(self):
        # Convert internal positions to the list of dicts format expected by engine
        pos_list = []
        for symbol, data in self.positions.items():
            pos_list.append({
                'symbol': symbol,
                'quantity': data['quantity'],
                'average_price': data['average_price'],
                'last_price': data.get('last_price', data['average_price']) # Use last_price if available
            })
        return pos_list
    
    def _get_positions_value(self):
        val = 0
        for symbol, data in self.positions.items():
            val += data['quantity'] * data.get('last_price', data['average_price'])
        return val

    def set_current_bar(self, symbol, bar: Candle):
        # Update position's last price if held
        if symbol in self.positions and self.positions[symbol]['quantity'] > 0:
            self.positions[symbol]['last_price'] = bar.close

    def _process_pending_orders(self):
        # Simplified: No actual order processing needed for these tests,
        # as we're not testing strategy logic but analytics generation.
        pass
    
    def place_order(self, order): # Mock a simple order placement
        # Simulate a trade execution and add to history for testing _convert_trades_to_dataframe
        # This is more for if the strategy itself was creating trades.
        # For testing analytics, we can directly set self.trade_history.
        pass


class TestBacktesterEngineAnalyticsIntegration(unittest.TestCase):

    def setUp(self):
        self.start_date = datetime.datetime(2023, 1, 1)
        self.end_date = datetime.datetime(2023, 1, 3)
        self.symbol = "TEST_SYM"
        self.timeframe_str = "1D" # String representation of timeframe

        self.sample_candles_list = [
            Candle(timestamp=self.start_date, symbol=self.symbol, open=100, high=105, low=99, close=102, volume=1000),
            Candle(timestamp=self.start_date + datetime.timedelta(days=1), symbol=self.symbol, open=102, high=107, low=101, close=105, volume=1200),
        ]
        
        # HDM needs data in a specific format if load_data is complex.
        # Let's assume get_all_data_sorted_by_timestamp is the key method to mock or control.
        self.hdm = MagicMock(spec=HistoricalDataManager) 
        
        # Prepare what HDM's get_all_data_sorted_by_timestamp should return
        self.market_data_feed = []
        for candle in self.sample_candles_list:
            self.market_data_feed.append(
                (candle.timestamp, {self.symbol: candle})
            )
        self.hdm.get_all_data_sorted_by_timestamp.return_value = self.market_data_feed
        
        self.mock_broker = MinimalMockBroker(initial_cash=100000)
        
        # Strategy setup
        self.strategy_config = {'param1': 10} # Dummy config
        self.dummy_strategy = DummyStrategy("DummyStratID", self.mock_broker, self.strategy_config)


    @patch('src.backtester.engine.PerformanceReporter')
    def test_analytics_report_generated_when_flag_is_true(self, MockPerformanceReporter):
        mock_reporter_instance = MockPerformanceReporter.return_value
        
        # Engine setup
        engine = BacktesterEngine(
            strategy=self.dummy_strategy, broker=self.mock_broker, historical_data_manager=self.hdm,
            symbols=[self.symbol], timeframe=self.timeframe_str,
            start_date=self.start_date, end_date=self.end_date,
            generate_analytics_report=True
        )
        
        # Mock trade history from broker
        self.mock_broker.trade_history = [
            {'symbol': self.symbol, 'side': 'BUY', 'quantity': 10, 'price': 100, 'timestamp': pd.Timestamp('2023-01-01 10:00:00'), 'pnl': 0, 'commission': 1}
        ]
        # The engine's run method populates its own portfolio_history.
        # We don't need to manually set engine.portfolio_history if the loop runs.

        engine.run()

        MockPerformanceReporter.assert_called_once()
        mock_reporter_instance.generate_quantstats_report.assert_called_once()
        mock_reporter_instance.plot_equity_curve.assert_called_once()


    @patch('src.backtester.engine.PerformanceReporter')
    def test_analytics_report_not_generated_when_flag_is_false(self, MockPerformanceReporter):
        engine = BacktesterEngine(
            strategy=self.dummy_strategy, broker=self.mock_broker, historical_data_manager=self.hdm,
            symbols=[self.symbol], timeframe=self.timeframe_str,
            start_date=self.start_date, end_date=self.end_date,
            generate_analytics_report=False # Explicitly False
        )
        engine.run()
        MockPerformanceReporter.assert_not_called()

        
    @patch('src.backtester.engine.PerformanceReporter')
    def test_trade_conversion_and_equity_curve_passed_correctly(self, MockPerformanceReporter):
        # 1. Setup Mock Broker to return specific trades
        mock_trade_history_data = [
            {'symbol': self.symbol, 'side': 'BUY', 'quantity': 10, 'price': 100.0, 'timestamp': pd.Timestamp('2023-01-01 10:00:00'), 'pnl': 20.0, 'commission': 1.0},
            {'symbol': self.symbol, 'side': 'SELL', 'quantity': 10, 'price': 102.0, 'timestamp': pd.Timestamp('2023-01-02 10:00:00'), 'pnl': -5.0, 'commission': 1.0, 'some_other_field': 'value'}
        ]
        self.mock_broker.trade_history = mock_trade_history_data

        # 2. Engine setup
        engine = BacktesterEngine(
            strategy=self.dummy_strategy, broker=self.mock_broker, historical_data_manager=self.hdm,
            symbols=[self.symbol], timeframe=self.timeframe_str,
            start_date=self.start_date, end_date=self.end_date,
            generate_analytics_report=True
        )
        
        # For equity curve, the engine's run loop will populate portfolio_history.
        # The sample_candles_list and MinimalMockBroker's behavior should generate a simple history.
        # Initial cash: 100000
        # Day 1 (2023-01-01): Candle close 102. Portfolio value based on this.
        # Day 2 (2023-01-02): Candle close 105.
        
        engine.run()

        MockPerformanceReporter.assert_called_once()
        call_args = MockPerformanceReporter.call_args
        
        # Check trades DataFrame
        trades_df_arg = call_args.kwargs['trades']
        self.assertIsInstance(trades_df_arg, pd.DataFrame)
        self.assertEqual(len(trades_df_arg), 2)
        self.assertEqual(trades_df_arg.loc[0, 'pnl'], 20.0)
        self.assertEqual(trades_df_arg.loc[1, 'pnl'], -5.0)
        self.assertTrue('pnl' in trades_df_arg.columns)
        self.assertTrue('commission' in trades_df_arg.columns)
        self.assertEqual(trades_df_arg['timestamp'].dtype, 'datetime64[ns]')
        self.assertEqual(trades_df_arg['price'].dtype, 'float64') # from pd.to_numeric

        # Check equity curve Series
        equity_series_arg = call_args.kwargs['equity_curve']
        self.assertIsInstance(equity_series_arg, pd.Series)
        # Based on the two candles and initial cash of 100000. No trades are made by DummyStrategy.
        # So equity curve should just be initial cash at each timestamp from market_data_feed.
        self.assertEqual(len(equity_series_arg), len(self.sample_candles_list)) 
        self.assertEqual(equity_series_arg.iloc[0], 100000) # Initial cash
        self.assertEqual(equity_series_arg.iloc[1], 100000) # Still initial cash as no trades
        self.assertEqual(equity_series_arg.index[0], pd.Timestamp('2023-01-01'))
        self.assertEqual(equity_series_arg.index[1], pd.Timestamp('2023-01-02'))
        self.assertTrue(equity_series_arg.index.is_monotonic_increasing)
        self.assertIsInstance(equity_series_arg.index, pd.DatetimeIndex)

        # Test duplicate timestamp handling in equity curve (more direct test)
        # Manually create portfolio_history for the engine to process
        engine.portfolio_history = [
            {'timestamp': pd.Timestamp('2023-01-01 00:00:00'), 'total_value': 100000},
            {'timestamp': pd.Timestamp('2023-01-01 17:00:00'), 'total_value': 100040},
            {'timestamp': pd.Timestamp('2023-01-01 17:00:00'), 'total_value': 100050}, # Duplicate
            {'timestamp': pd.Timestamp('2023-01-02 17:00:00'), 'total_value': 99980},
        ]
        # Re-trigger the analytics part (simplified for this test)
        # In a real scenario, you might need a more focused way to test _generate_analytics_report part
        engine._BacktesterEngine__convert_trades_to_dataframe = MagicMock(return_value=pd.DataFrame(mock_trade_history_data)) # mock conversion
        
        # This is a bit of a hack to re-run just the reporting part.
        # A cleaner way might be to refactor the reporting logic into a separate method in BacktesterEngine.
        # For now, let's call the reporter directly with what the engine would compute.
        
        timestamps_ph = [e['timestamp'] for e in engine.portfolio_history]
        values_ph = [e['total_value'] for e in engine.portfolio_history]
        temp_df_ph = pd.DataFrame({'timestamp': pd.to_datetime(timestamps_ph), 'value': values_ph})
        temp_df_ph = temp_df_ph.sort_values('timestamp').groupby('timestamp').last() # Duplicate handling
        equity_curve_series_manual = pd.Series(temp_df_ph['value'], name="Equity")

        self.assertEqual(len(equity_curve_series_manual), 3)
        self.assertEqual(equity_curve_series_manual.iloc[1], 100050) # Last value for duplicate timestamp
        self.assertEqual(equity_curve_series_manual.index[1], pd.Timestamp('2023-01-01 17:00:00'))


    @patch('src.backtester.engine.PerformanceReporter')
    @patch('src.backtester.engine.pd.Timestamp') # To control the timestamp in filenames
    def test_report_filename_format(self, MockTimestamp, MockPerformanceReporter):
        mock_reporter_instance = MockPerformanceReporter.return_value
        
        # Mock pd.Timestamp.now() to return a fixed time for predictable filenames
        fixed_timestamp_now = pd.Timestamp('2023-02-15 10:30:00')
        MockTimestamp.now.return_value = fixed_timestamp_now
        expected_time_str = fixed_timestamp_now.strftime('%Y%m%d_%H%M%S')

        engine = BacktesterEngine(
            strategy=self.dummy_strategy, broker=self.mock_broker, historical_data_manager=self.hdm,
            symbols=[self.symbol], timeframe=self.timeframe_str,
            start_date=self.start_date, end_date=self.end_date,
            generate_analytics_report=True
        )
        engine.run()
        
        report_call_args = mock_reporter_instance.generate_quantstats_report.call_args
        plot_call_args = mock_reporter_instance.plot_equity_curve.call_args

        self.assertIn('output_path', report_call_args.kwargs)
        report_path = report_call_args.kwargs['output_path']
        expected_report_name = f"backtest_report_{self.dummy_strategy.__class__.__name__}_{expected_time_str}.html"
        self.assertEqual(report_path, expected_report_name)

        self.assertIn('output_path', plot_call_args.kwargs)
        plot_path = plot_call_args.kwargs['output_path']
        expected_plot_name = f"equity_curve_{self.dummy_strategy.__class__.__name__}_{expected_time_str}.png"
        self.assertEqual(plot_path, expected_plot_name)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

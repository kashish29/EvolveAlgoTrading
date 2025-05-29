import unittest
from unittest.mock import MagicMock, call
import pandas as pd
from datetime import datetime, timezone

from src.live_trader.event_handler import DataFeedSimulator # Class under test
from src.broker_api.mock_fyers_client import MockFyersClient as ActualMockFyersClient # For type hinting with spec
from src.core.models import Candle, Order
from src.core.enums import Timeframe, OrderStatus, OrderSide, OrderType

class TestDataFeedSimulator(unittest.TestCase):
    """
    Test suite for the DataFeedSimulator class.
    """

    def setUp(self):
        """
        Set up common sample data and mocks.
        """
        self.mock_broker = MagicMock(spec=ActualMockFyersClient)
        self.mock_broker.current_time = None # Initialize current_time
        
        # Sample DataFrame structure
        self.sample_data = {
            'timestamp': [datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc), datetime(2023, 1, 1, 10, 5, tzinfo=timezone.utc)],
            'open': [100, 101],
            'high': [102, 103],
            'low': [99, 100],
            'close': [101, 102],
            'volume': [1000, 1050],
            'symbol': ['SYM1', 'SYM1'],
            'timeframe': ['MINUTE_1', 'MINUTE_1'] # Example timeframe strings
        }
        self.sample_df = pd.DataFrame(self.sample_data)

    # Test Case 1: Yields Candle Events Correctly
    def test_yields_candle_events_correctly(self):
        # b. Configure mock_broker
        self.mock_broker.get_simulated_order_updates.return_value = []
        
        # c. Instantiate DataFeedSimulator
        simulator = DataFeedSimulator(
            historical_data=self.sample_df.copy(),
            mock_broker=self.mock_broker # Changed broker_client to mock_broker
        )
        
        # d. Collect events
        events = list(simulator.generate_events())
        
        # e. Assert 2 Candle events
        self.assertEqual(len(events), 2)
        self.assertTrue(all(isinstance(event, Candle) for event in events))
        
        # f. Verify attributes
        candle1_event = events[0]
        self.assertEqual(candle1_event.timestamp, self.sample_df['timestamp'].iloc[0])
        self.assertEqual(candle1_event.symbol, 'SYM1')
        self.assertEqual(candle1_event.open, self.sample_df['open'].iloc[0])
        self.assertEqual(candle1_event.high, self.sample_df['high'].iloc[0])
        self.assertEqual(candle1_event.low, self.sample_df['low'].iloc[0])
        self.assertEqual(candle1_event.close, self.sample_df['close'].iloc[0])
        self.assertEqual(candle1_event.volume, self.sample_df['volume'].iloc[0])
        self.assertEqual(candle1_event.timeframe, Timeframe.MINUTE_1) # Check conversion

        candle2_event = events[1]
        self.assertEqual(candle2_event.timestamp, self.sample_df['timestamp'].iloc[1])
        self.assertEqual(candle2_event.symbol, 'SYM1')
        self.assertEqual(candle2_event.close, self.sample_df['close'].iloc[1])
        self.assertEqual(candle2_event.timeframe, Timeframe.MINUTE_1)

        # g. Assert mock_broker calls
        self.mock_broker.set_current_bar.assert_has_calls([
            call(events[0].symbol, events[0]),
            call(events[1].symbol, events[1])
        ])
        self.assertEqual(self.mock_broker.set_current_bar.call_count, 2)
        
        self.mock_broker._process_pending_orders.assert_has_calls([call(), call()])
        self.assertEqual(self.mock_broker._process_pending_orders.call_count, 2)

        # Check current_time was set (it's set before set_current_bar)
        # The attribute is set directly, so we can check its final value or mock __setattr__ if needed,
        # but simpler to check the number of times it would have been set.
        # For this, we'd need to track calls to setting current_time or check its value if generate_events was a generator.
        # Here, since events are collected, current_time will be the last timestamp.
        self.assertEqual(self.mock_broker.current_time, self.sample_df['timestamp'].iloc[1])


    # Test Case 2: Yields Candle and Order Update Events
    def test_yields_candle_and_order_update_events(self):
        # b. Create mock order update
        mock_order_update = Order(
            id="test_order_123", symbol="SYM1", quantity=10, side=OrderSide.BUY, # Changed order_id to id
            order_type=OrderType.LIMIT, price=100.0, status=OrderStatus.COMPLETED,
            timestamp=datetime.now(timezone.utc)
        )
        
        # c. Configure mock_broker
        self.mock_broker.get_simulated_order_updates.side_effect = [[], [mock_order_update]]
        
        # d. Instantiate and collect events
        simulator = DataFeedSimulator(
            historical_data=self.sample_df.copy(),
            mock_broker=self.mock_broker # Changed broker_client to mock_broker
        )
        events = list(simulator.generate_events())
        
        # e. Assert 3 events
        self.assertEqual(len(events), 3)
        self.assertIsInstance(events[0], Candle)
        self.assertIsInstance(events[1], Candle) # Second candle event
        self.assertIsInstance(events[2], Order)  # Order update event
        
        self.assertEqual(events[0].timestamp, self.sample_df['timestamp'].iloc[0])
        self.assertEqual(events[1].timestamp, self.sample_df['timestamp'].iloc[1])
        self.assertEqual(events[2].id, "test_order_123") # Changed order_id to id
        self.assertEqual(events[2].status, OrderStatus.COMPLETED)


    # Test Case 3: Uses Default Symbol and Timeframe
    def test_uses_default_symbol_and_timeframe(self):
        # a. DataFrame missing symbol and timeframe
        data_no_sym_tf = {
            'timestamp': [datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)],
            'open': [100], 'high': [102], 'low': [99], 'close': [101], 'volume': [1000]
        }
        df_no_sym_tf = pd.DataFrame(data_no_sym_tf)
        
        self.mock_broker.get_simulated_order_updates.return_value = []
        
        # b. Instantiate with defaults
        simulator = DataFeedSimulator(
            historical_data=df_no_sym_tf,
            mock_broker=self.mock_broker, # Changed broker_client to mock_broker
            default_symbol="DEF_SYM",
            default_timeframe=Timeframe.DAY_1
        )
        
        # c. Collect events
        events = list(simulator.generate_events())
        
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], Candle)
        self.assertEqual(events[0].symbol, "DEF_SYM")
        self.assertEqual(events[0].timeframe, Timeframe.DAY_1)


    # Test Case 4: Handles Invalid Timeframe String
    def test_handles_invalid_timeframe_string(self):
        # a. DataFrame with invalid timeframe string
        data_bad_tf = self.sample_df.copy()
        data_bad_tf.loc[0, 'timeframe'] = "bad_tf" # First row has bad timeframe
        
        self.mock_broker.get_simulated_order_updates.return_value = []
        
        # b. Instantiate with default timeframe
        simulator = DataFeedSimulator(
            historical_data=data_bad_tf,
            mock_broker=self.mock_broker, # Changed broker_client to mock_broker
            default_timeframe=Timeframe.HOUR_1
        )
        
        # c. Collect events and assert
        # Optional: Check for log warning
        with self.assertLogs(level='WARNING') as log_cm:
            events = list(simulator.generate_events())
        
        self.assertTrue(any(f"Invalid timeframe string 'bad_tf' in data, using default {Timeframe.HOUR_1.value}" in msg for msg in log_cm.output))
        
        self.assertEqual(len(events), 2) # Both events should be processed
        self.assertIsInstance(events[0], Candle)
        self.assertEqual(events[0].timeframe, Timeframe.HOUR_1) # Uses default
        
        self.assertIsInstance(events[1], Candle)
        self.assertEqual(events[1].timeframe, Timeframe.MINUTE_1) # Uses valid one from DF for second row


    # Test Case 5: Handles Missing Essential Column (KeyError)
    def test_handles_missing_essential_column(self):
        # a. DataFrame missing 'close' column
        data_missing_col = self.sample_df.copy().drop(columns=['close'])
        
        self.mock_broker.get_simulated_order_updates.return_value = []
        
        # b. Instantiate
        simulator = DataFeedSimulator(
            historical_data=data_missing_col,
            mock_broker=self.mock_broker # Changed broker_client to mock_broker
        )
        
        # c. Collect events and assert
        # Optional: Check for log error
        with self.assertLogs(level='ERROR') as log_cm:
            events = list(simulator.generate_events())
        
        self.assertTrue(any("Missing expected column in historical_data: 'close'" in msg for msg in log_cm.output))
        self.assertEqual(len(events), 0) # No Candle events yielded due to error

if __name__ == '__main__':
    unittest.main()

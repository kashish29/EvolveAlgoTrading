import unittest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone

from src.live_trader.event_handler import EventHandler, DataFeedSimulator # EventHandler is under test
from src.strategies.base_strategy import BaseStrategy # For spec
from src.broker_api.base_broker_client import BaseBrokerClient # For spec
from src.core.models import Candle, Order
from src.core.enums import Timeframe, OrderSide, OrderStatus, OrderType # Added OrderType

class TestEventHandlerRunSimulationLoop(unittest.TestCase):
    """
    Test suite for the EventHandler.run_simulation_loop() method.
    """

    def setUp(self):
        """
        Set up mocks and an EventHandler instance for each test.
        """
        self.mock_strategy = MagicMock(spec=BaseStrategy)
        self.mock_strategy.on_bar = MagicMock() # Ensure methods exist on the mock
        self.mock_strategy.on_order_update = MagicMock()

        self.mock_broker_client = MagicMock(spec=BaseBrokerClient)
        
        self.mock_data_feed_simulator = MagicMock(spec=DataFeedSimulator)
        self.mock_data_feed_simulator.generate_events = MagicMock() # Ensure method exists

        self.event_handler = EventHandler(
            strategy=self.mock_strategy,
            broker_client=self.mock_broker_client, # Though not directly used by run_simulation_loop
            data_feed_simulator=self.mock_data_feed_simulator
        )

        # Sample events for use in tests
        self.ts1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        self.ts2 = datetime(2023, 1, 1, 10, 5, tzinfo=timezone.utc)
        
        self.sample_candle1 = Candle(
            timestamp=self.ts1, symbol="SYM1", timeframe=Timeframe.MINUTE_1,
            open=100, high=101, low=99, close=100, volume=1000
        )
        self.sample_candle2 = Candle(
            timestamp=self.ts2, symbol="SYM1", timeframe=Timeframe.MINUTE_1,
            open=101, high=102, low=100, close=101, volume=1200
        )
        self.sample_order1 = Order(
            id="order1", symbol="SYM1", quantity=10, side=OrderSide.BUY, # Changed order_id to id
            order_type=OrderType.LIMIT, price=100.0, status=OrderStatus.COMPLETED,
            timestamp=self.ts1
        )
        self.sample_order2 = Order(
            id="order2", symbol="SYM1", quantity=5, side=OrderSide.SELL, # Changed order_id to id
            order_type=OrderType.MARKET, status=OrderStatus.ACCEPTED,
            timestamp=self.ts2
        )

    # Test Case 1: Processes Candle Events
    def test_processes_candle_events(self):
        self.mock_data_feed_simulator.generate_events.return_value = [self.sample_candle1, self.sample_candle2]
        
        self.event_handler.run_simulation_loop()
        
        self.assertEqual(self.mock_strategy.on_bar.call_count, 2)
        self.mock_strategy.on_bar.assert_any_call({self.sample_candle1.symbol: self.sample_candle1})
        self.mock_strategy.on_bar.assert_any_call({self.sample_candle2.symbol: self.sample_candle2})
        self.mock_strategy.on_order_update.assert_not_called()

    # Test Case 2: Processes Order Update Events
    def test_processes_order_update_events(self):
        self.mock_data_feed_simulator.generate_events.return_value = [self.sample_order1, self.sample_order2]
        
        self.event_handler.run_simulation_loop()
        
        self.assertEqual(self.mock_strategy.on_order_update.call_count, 2)
        self.mock_strategy.on_order_update.assert_any_call(self.sample_order1)
        self.mock_strategy.on_order_update.assert_any_call(self.sample_order2)
        self.mock_strategy.on_bar.assert_not_called()

    # Test Case 3: Processes Mixed Event Types
    def test_processes_mixed_event_types(self):
        self.mock_data_feed_simulator.generate_events.return_value = [self.sample_candle1, self.sample_order1]
        
        self.event_handler.run_simulation_loop()
        
        self.mock_strategy.on_bar.assert_called_once_with({self.sample_candle1.symbol: self.sample_candle1})
        self.mock_strategy.on_order_update.assert_called_once_with(self.sample_order1)

    # Test Case 4: Handles Unknown Event Type
    def test_handles_unknown_event_type(self):
        unknown_event = MagicMock() # Not a Candle or Order
        self.mock_data_feed_simulator.generate_events.return_value = [unknown_event]
        
        # Optional: Check for log warning if EventHandler implements logging for unknown types
        with self.assertLogs(level='WARNING') as log_cm:
            self.event_handler.run_simulation_loop()
        
        self.assertTrue(any(f"Received unknown event type: {type(unknown_event)}" in msg for msg in log_cm.output))

        self.mock_strategy.on_bar.assert_not_called()
        self.mock_strategy.on_order_update.assert_not_called()

    # Test Case 5: Continues After Exception in Strategy Handler
    def test_continues_after_exception_in_strategy_handler(self):
        # Configure on_order_update to raise an exception on the first call
        self.mock_strategy.on_order_update.side_effect = [Exception("Test error from on_order_update"), None]
        
        self.mock_data_feed_simulator.generate_events.return_value = [
            self.sample_candle1, self.sample_order1, self.sample_candle2
        ]
        
        # Optional: Check for log error if EventHandler implements logging for exceptions
        with self.assertLogs(level='ERROR') as log_cm:
            self.event_handler.run_simulation_loop()
        
        self.assertTrue(any("Error processing event" in msg and 
                            f"Order(id='{self.sample_order1.id}'" in msg and # Check part of order representation
                            "Test error from on_order_update" in msg 
                            for msg in log_cm.output), "Expected log message for strategy error not found or incorrect.")

        self.assertEqual(self.mock_strategy.on_bar.call_count, 2)
        self.mock_strategy.on_bar.assert_any_call({self.sample_candle1.symbol: self.sample_candle1})
        self.mock_strategy.on_bar.assert_any_call({self.sample_candle2.symbol: self.sample_candle2})
        
        # on_order_update was called once (and raised an error)
        self.mock_strategy.on_order_update.assert_called_once_with(self.sample_order1)


if __name__ == '__main__':
    unittest.main()

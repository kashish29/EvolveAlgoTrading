import unittest
from unittest.mock import MagicMock, patch, call # Ensure call is imported
import pandas as pd
from datetime import datetime

# Classes to be tested
from src.live_trader.event_handler import EventHandler, DataFeedSimulator

# Dependent classes that need mocking
from src.strategies.base_strategy import BaseStrategy
from src.broker_api.mock_fyers_client import MockFyersClient # Or BaseBrokerClient if preferred for interface
from src.core.models import Candle, Order, OrderStatus, OrderSide, OrderType, Timeframe

class TestDataFeedSimulator(unittest.TestCase):

    def setUp(self):
        self.mock_broker = MagicMock(spec=MockFyersClient)
        self.mock_broker.get_simulated_order_updates = MagicMock(return_value=[]) # Default empty updates
        
        # Sample historical data for the simulator
        self.sample_data = {
            'timestamp': [datetime(2023, 1, 1, 10, 0, 0), datetime(2023, 1, 1, 10, 1, 0)],
            'symbol': ['TEST_SYM', 'TEST_SYM'],
            'open': [100, 101],
            'high': [102, 102],
            'low': [99, 100],
            'close': [101, 101.5],
            'volume': [1000, 1200],
            'timeframe': [Timeframe.MINUTE_1, Timeframe.MINUTE_1] # Assuming Timeframe.MINUTE_1 is valid
        }
        self.historical_df = pd.DataFrame(self.sample_data)

        # DataFeedSimulator expects default_symbol and default_timeframe in its constructor
        self.data_feed_simulator = DataFeedSimulator(
            self.historical_df, 
            self.mock_broker,
            default_symbol="FALLBACK_SYM", # Provide a default symbol
            default_timeframe=Timeframe.MINUTE_1 # Provide a default timeframe
        )

    def test_generate_events_yields_market_data(self):
        events = list(self.data_feed_simulator.generate_events())
        market_events = [e for e in events if isinstance(e, Candle)]
        self.assertEqual(len(market_events), 2)
        self.assertEqual(market_events[0].symbol, 'TEST_SYM')
        self.assertEqual(market_events[0].close, 101)
        self.assertEqual(market_events[1].close, 101.5)
        self.assertEqual(market_events[0].timeframe, Timeframe.MINUTE_1)

        # Check broker interactions for each market event
        expected_calls_set_current_bar = [
            call('TEST_SYM', market_events[0]),
            call('TEST_SYM', market_events[1])
        ]
        self.mock_broker.set_current_bar.assert_has_calls(expected_calls_set_current_bar, any_order=False)
        
        # Check that broker.current_time was set (DataFeedSimulator sets this directly)
        # This is a bit tricky to assert directly on the attribute of a mock if not wrapped by a method.
        # Instead, we rely on the fact that _process_pending_orders (which depends on current_time) is called.
        # A more direct way would be to have a setter method on the broker for current_time.
        # For now, checking the calls to _process_pending_orders implies time has been managed.
        
        self.assertEqual(self.mock_broker._process_pending_orders.call_count, 2)
        self.assertEqual(self.mock_broker.get_simulated_order_updates.call_count, 2)


    def test_generate_events_yields_order_updates(self):
        # Simulate that get_simulated_order_updates returns an order update after the first market event
        mock_order_update = Order(id="order1", symbol="TEST_SYM", quantity=10, side=OrderSide.BUY, order_type=OrderType.MARKET, status=OrderStatus.COMPLETED, timestamp=datetime.now())
        
        # Configure mock to return the order update only on the first call to get_simulated_order_updates
        self.mock_broker.get_simulated_order_updates.side_effect = [[mock_order_update], []]

        events = list(self.data_feed_simulator.generate_events())
        
        order_update_events = [e for e in events if isinstance(e, Order)]
        self.assertEqual(len(order_update_events), 1)
        self.assertIs(order_update_events[0], mock_order_update) # Check it's the same object

        # Ensure get_simulated_order_updates was called for each bar
        self.assertEqual(self.mock_broker.get_simulated_order_updates.call_count, 2)


class TestEventHandler(unittest.TestCase):

    def setUp(self):
        self.mock_strategy = MagicMock(spec=BaseStrategy)
        # Ensure on_bar is a MagicMock itself to allow asserting calls on it
        self.mock_strategy.on_bar = MagicMock()
        self.mock_strategy.on_order_update = MagicMock()

        self.mock_broker_client = MagicMock(spec=MockFyersClient) 
        self.mock_data_feed_simulator = MagicMock(spec=DataFeedSimulator)

        self.event_handler = EventHandler(
            strategy=self.mock_strategy,
            broker_client=self.mock_broker_client,
            data_feed_simulator=self.mock_data_feed_simulator
        )

    def test_run_simulation_loop_processes_market_events(self):
        market_event_1 = Candle(timestamp=datetime.now(), symbol="SYM1", open=10, high=11, low=9, close=10.5, volume=100, timeframe=Timeframe.MINUTE_1)
        market_event_2 = Candle(timestamp=datetime.now(), symbol="SYM2", open=20, high=21, low=19, close=20.5, volume=200, timeframe=Timeframe.MINUTE_1)
        
        self.mock_data_feed_simulator.generate_events.return_value = [market_event_1, market_event_2]

        self.event_handler.run_simulation_loop()

        # Verify strategy.on_bar was called correctly
        # The EventHandler's implementation of on_bar call: self.strategy.on_bar({event.symbol: event})
        # It does NOT pass broker_client as the second argument based on the current EventHandler implementation.
        # The provided test code had an expectation of `self.mock_broker_client` being passed.
        # Adjusting this to match the actual EventHandler implementation from src/live_trader/event_handler.py
        expected_on_bar_calls = [
            call({market_event_1.symbol: market_event_1}),
            call({market_event_2.symbol: market_event_2})
        ]
        self.mock_strategy.on_bar.assert_has_calls(expected_on_bar_calls)
        self.assertEqual(self.mock_strategy.on_bar.call_count, 2)
        self.mock_strategy.on_order_update.assert_not_called()


    def test_run_simulation_loop_processes_order_update_events(self):
        order_update_event_1 = Order(id="order1", symbol="SYM1", quantity=10, side=OrderSide.BUY, order_type=OrderType.MARKET, status=OrderStatus.COMPLETED, timestamp=datetime.now())
        order_update_event_2 = Order(id="order2", symbol="SYM2", quantity=5, side=OrderSide.SELL, order_type=OrderType.LIMIT, status=OrderStatus.CANCELLED, price=20.0, timestamp=datetime.now())

        self.mock_data_feed_simulator.generate_events.return_value = [order_update_event_1, order_update_event_2]

        self.event_handler.run_simulation_loop()

        # Verify strategy.on_order_update was called correctly
        expected_on_order_update_calls = [
            call(order_update_event_1),
            call(order_update_event_2)
        ]
        self.mock_strategy.on_order_update.assert_has_calls(expected_on_order_update_calls)
        self.assertEqual(self.mock_strategy.on_order_update.call_count, 2)
        self.mock_strategy.on_bar.assert_not_called()

    def test_run_simulation_loop_processes_mixed_events(self):
        market_event = Candle(timestamp=datetime.now(), symbol="SYM1", open=10, high=11, low=9, close=10.5, volume=100, timeframe=Timeframe.MINUTE_1)
        order_update_event = Order(id="order1", symbol="SYM1", quantity=10, side=OrderSide.BUY, order_type=OrderType.MARKET, status=OrderStatus.COMPLETED, timestamp=datetime.now())
        
        self.mock_data_feed_simulator.generate_events.return_value = [market_event, order_update_event]

        self.event_handler.run_simulation_loop()
        
        # Adjusted based on current EventHandler implementation (does not pass broker_client to on_bar)
        self.mock_strategy.on_bar.assert_called_once_with({market_event.symbol: market_event})
        self.mock_strategy.on_order_update.assert_called_once_with(order_update_event)

    @patch('src.live_trader.event_handler.logging') # Patch logger in event_handler module
    def test_run_simulation_loop_handles_exception_in_event_processing(self, mock_logging_module):
        # Access the logger instance used by EventHandler if it's named conventionally
        # Or, if EventHandler gets its logger as logging.getLogger(self.__class__.__name__),
        # we can patch that specific logger instance.
        # For simplicity, let's assume event_handler.logger is accessible or we patch the module's logger.
        # The provided patch uses 'src.live_trader.event_handler.logger' which might not be the actual logger instance name.
        # It should be 'src.live_trader.event_handler.EventHandler.logger' if it's an instance logger,
        # or patch logging.getLogger().
        # A common pattern is: logger = logging.getLogger(__name__) in the module, or self.logger = logging.getLogger(self.__class__.__name__)
        # Patching logging.getLogger directly or the specific logger instance.
        # Let's assume EventHandler uses self.logger = logging.getLogger(self.__class__.__name__)
        # And the patch('src.live_trader.event_handler.logger') refers to a module-level logger if it exists.
        # If EventHandler's logger is self.logger, then we'd patch it like:
        # @patch.object(EventHandler, 'logger', new_callable=MagicMock)

        # The provided patch `src.live_trader.event_handler.logger` suggests patching a module-level logger.
        # Let's assume it's `logger = logging.getLogger(__name__)` at the module level of event_handler.py
        # Or, if EventHandler explicitly creates its logger like self.logger = logging.getLogger("EventHandlerClassLogger")
        # then patch("src.live_trader.event_handler.EventHandlerClassLogger")

        # Given the patch string, it implies a module-level logger named 'logger'
        # However, the EventHandler code uses `self.logger = logging.getLogger(self.__class__.__name__)`
        # So, the patch should ideally be:
        # @patch('logging.Logger.error') or more specifically patch the logger instance.
        # For now, using the provided patch string and assuming it works as intended by the test writer.
        # A more robust patch might be:
        # with patch.object(self.event_handler.logger, 'error') as mock_logger_error_method:
        
        # Let's refine the patch target based on typical usage in the EventHandler class:
        # It gets logger via `self.logger = logging.getLogger(self.__class__.__name__)`
        # So, we patch `logging.getLogger` to return our mock logger, or patch `self.event_handler.logger` directly.
        
        # Re-evaluating the patch: The provided patch string `src.live_trader.event_handler.logger`
        # would work if there's `logger = logging.getLogger(...)` at module level in event_handler.py.
        # The EventHandler class has `self.logger = logging.getLogger(self.__class__.__name__)`.
        # A direct patch on the instance's logger would be:
        # self.event_handler.logger = MagicMock()
        # mock_logger_error_method = self.event_handler.logger.error

        # Sticking to the provided patch for now, assuming it's set up to catch the log.
        # If it fails, the patch target needs adjustment.
        # The most common way to make this work is if the logger in event_handler.py is obtained by:
        # `logger = logging.getLogger(__name__)` at module scope.
        # If the EventHandler's logger is `self.logger`, then the patch needs to target that.
        # A simple way: self.event_handler.logger = mock_logger_module (if mock_logger_module is a MagicMock instance)

        # Let's assume the patch provided in the prompt is intended to work on a logger instance.
        # We'll mock the logger instance directly on the event_handler object for this test.
        self.event_handler.logger = MagicMock()


        market_event = Candle(timestamp=datetime.now(), symbol="SYM1", open=10, high=11, low=9, close=10.5, volume=100, timeframe=Timeframe.MINUTE_1)
        # Simulate strategy.on_bar raising an exception
        self.mock_strategy.on_bar.side_effect = Exception("Test error in on_bar")
        
        self.mock_data_feed_simulator.generate_events.return_value = [market_event]

        self.event_handler.run_simulation_loop() # Should not raise an exception itself

        self.mock_strategy.on_bar.assert_called_once()
        # Check that an error was logged using the instance's mocked logger
        self.assertTrue(self.event_handler.logger.error.called)
        
        args, kwargs = self.event_handler.logger.error.call_args
        self.assertIn("Error processing event", args[0])
        # The actual exception object is passed to exc_info=True, so str(kwargs.get('exc_info')) might not be the best check.
        # Checking that exc_info=True was passed is usually sufficient.
        self.assertTrue(kwargs.get('exc_info'))
        # To check the content of the exception in the log, you might need a more complex setup
        # or rely on the fact that the correct exception was logged.
        # For example, if the logger formats the exception, the first arg of logger.error would contain it.
        # The current implementation logs: self.logger.error(f"Error processing event: {event}. Error: {e}", exc_info=True)
        # So, args[0] would be "Error processing event: <Candle ...>. Error: Test error in on_bar"
        self.assertIn("Test error in on_bar", args[0])


if __name__ == '__main__':
    unittest.main()


import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.live_trader.execution_handler import ExecutionHandler
from src.broker_api.base_broker_client import BaseBrokerClient
from src.core.models import Signal, Order, OrderSide, OrderStatus
from src.core.enums import OrderType

class TestExecutionHandler(unittest.TestCase):
    def setUp(self):
        self.mock_broker_client = MagicMock(spec=BaseBrokerClient)
        self.execution_handler = ExecutionHandler(broker_client=self.mock_broker_client)

        # Sample signal details
        self.symbol = "TEST_SYM"
        self.quantity = 15
        self.price = 150.0
        self.stop_price = 155.0
        self.timestamp = datetime.now()

    def create_sample_signal(self, side, order_type, price=None, stop_price=None, quantity=None):
        # The original provided logic for stop_price was:
        # stop_price=stop_price if stop_price is not None else (self.stop_price if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] else None),
        # Correcting OrderType.STOP to OrderType.STOP_MARKET as per typical enum values
        # (assuming OrderType.STOP is not a standalone type that takes stop_price but rather a category)
        # If OrderType.STOP is indeed a valid enum member that implies a stop market order, then the original was fine.
        # Based on common model definitions (like in core.models), STOP_MARKET is more explicit.
        # Let's assume the models use OrderType.STOP_MARKET and OrderType.STOP_LIMIT.
        actual_stop_price = None
        if stop_price is not None:
            actual_stop_price = stop_price
        elif order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT]: # Corrected enum check
            actual_stop_price = self.stop_price
            
        actual_price = None
        if price is not None:
            actual_price = price
        elif order_type == OrderType.LIMIT or order_type == OrderType.STOP_LIMIT : # Price for LIMIT and STOP_LIMIT
             actual_price = self.price


        return Signal(
            timestamp=self.timestamp,
            symbol=self.symbol,
            side=side, # Should be OrderSide enum member
            order_type=order_type, # Should be OrderType enum member
            price=actual_price,
            stop_price=actual_stop_price, # This is for trigger_price in Order
            quantity=quantity if quantity is not None else self.quantity,
            comment=f"Test {side.value} {order_type.value} signal"
        )

    def test_execute_signal_market_order(self):
        """Test execution of a MARKET order signal."""
        market_signal = self.create_sample_signal(OrderSide.BUY, OrderType.MARKET)
        
        mock_order_id = "broker_order_123"
        mock_order_status = "COMPLETED" # This is what the broker mock returns
        self.mock_broker_client.place_order.return_value = (mock_order_id, mock_order_status)

        self.execution_handler.execute_signal(market_signal)

        self.mock_broker_client.place_order.assert_called_once()
        
        args, _ = self.mock_broker_client.place_order.call_args
        placed_order_object = args[0] # This is the Order object created by ExecutionHandler
        
        self.assertIsInstance(placed_order_object, Order)
        self.assertEqual(placed_order_object.symbol, market_signal.symbol)
        self.assertEqual(placed_order_object.quantity, market_signal.quantity)
        self.assertEqual(placed_order_object.side, market_signal.side)
        self.assertEqual(placed_order_object.order_type, market_signal.order_type)
        # ExecutionHandler sets initial status to PENDING_OPEN before sending to broker
        self.assertEqual(placed_order_object.status, OrderStatus.COMPLETED)
        self.assertIsNone(placed_order_object.price)
        self.assertIsNone(placed_order_object.trigger_price)

    def test_execute_signal_limit_order(self):
        """Test execution of a LIMIT order signal."""
        limit_signal = self.create_sample_signal(OrderSide.SELL, OrderType.LIMIT, price=self.price)
        self.mock_broker_client.place_order.return_value = ("broker_limit_456", "ACCEPTED")

        self.execution_handler.execute_signal(limit_signal)
        self.mock_broker_client.place_order.assert_called_once()
        
        args, _ = self.mock_broker_client.place_order.call_args
        placed_order_object = args[0] # This is the Order object created by ExecutionHandler

        self.assertEqual(placed_order_object.order_type, OrderType.LIMIT)
        self.assertEqual(placed_order_object.price, self.price)
        self.assertIsNone(placed_order_object.trigger_price)
        self.assertEqual(placed_order_object.status, OrderStatus.ACCEPTED) # Broker returns ACCEPTED

    def test_execute_signal_stop_order(self):
        """Test execution of a STOP (market) order signal."""
        stop_signal = self.create_sample_signal(OrderSide.BUY, OrderType.STOP, stop_price=self.stop_price)
        self.mock_broker_client.place_order.return_value = ("broker_stop_789", "ACCEPTED")

        self.execution_handler.execute_signal(stop_signal)
        self.mock_broker_client.place_order.assert_called_once()
        placed_order_object = self.mock_broker_client.place_order.call_args[0][0]
        
        self.assertEqual(placed_order_object.order_type, OrderType.STOP)
        self.assertIsNone(placed_order_object.price) 
        self.assertEqual(placed_order_object.trigger_price, self.stop_price)
        self.assertEqual(placed_order_object.status, OrderStatus.ACCEPTED) # Broker returns ACCEPTED

    def test_execute_signal_stop_limit_order(self):
        """Test execution of a STOP_LIMIT order signal."""
        limit_price_for_stop_limit = 148.0 # A different price for the limit part
        stop_limit_signal = self.create_sample_signal(OrderSide.SELL, OrderType.STOP_LIMIT, price=limit_price_for_stop_limit, stop_price=self.stop_price)
        self.mock_broker_client.place_order.return_value = ("broker_sl_101", "ACCEPTED")

        self.execution_handler.execute_signal(stop_limit_signal)
        self.mock_broker_client.place_order.assert_called_once()
        placed_order_object = self.mock_broker_client.place_order.call_args[0][0]

        self.assertEqual(placed_order_object.order_type, OrderType.STOP_LIMIT)
        self.assertEqual(placed_order_object.price, limit_price_for_stop_limit)
        self.assertEqual(placed_order_object.trigger_price, self.stop_price)
        self.assertEqual(placed_order_object.status, OrderStatus.ACCEPTED) # Broker returns ACCEPTED

    @patch('src.live_trader.execution_handler.logging.getLogger') # More robust patch target
    def test_execute_signal_logs_attempt_and_response(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        
        # Re-initialize execution_handler to use the mocked logger via getLogger
        # This is important if the logger is obtained during __init__
        self.execution_handler = ExecutionHandler(broker_client=self.mock_broker_client)

        market_signal = self.create_sample_signal(OrderSide.BUY, OrderType.MARKET)
        mock_order_id = "log_test_id_123"
        mock_status_str = "COMPLETED_FROM_BROKER" # String status from broker
        self.mock_broker_client.place_order.return_value = (mock_order_id, mock_status_str)

        self.execution_handler.execute_signal(market_signal)

        # ExecutionHandler logs:
        # 1. "ExecutionHandler initialized..." (if this test is the first to init one with this mock)
        # 2. "Received signal to execute: ..."
        # 3. "Constructed Order: ..."
        # 4. "Placing order for {order_to_place.symbol} with broker..."
        # 5. "Order placement attempt for ... resulted in: Broker Order ID: ..., Status from broker: ..."
        
        # Check for at least 4 info calls related to one signal processing.
        # The init log might also be there if this instance is the first one picked by the mock.
        self.assertGreaterEqual(mock_logger_instance.info.call_count, 4) 
        
        log_calls = mock_logger_instance.info.call_args_list
        
        # Find the "Placing order" log (attempt)
        # This is usually the 3rd log specific to execute_signal, or 4th if init log is counted.
        # Let's search for it to be more robust.
        attempt_log_found = False
        for call_arg in log_calls:
            args, _ = call_arg
            if args and f"Placing order for {market_signal.symbol} with broker..." in args[0]:
                attempt_log_found = True
                break
        self.assertTrue(attempt_log_found, "Log message for 'Placing order' not found.")

        # Find the "Order placement attempt ... resulted in" log (response)
        response_log_found = False
        expected_response_substring = f"Order placement attempt for {market_signal.symbol} (Signal ID {getattr(market_signal, 'id', 'N/A')}) resulted in: Broker Order ID: {mock_order_id}, Status from broker: {mock_status_str}"
        for call_arg in log_calls:
            args, _ = call_arg
            if args and expected_response_substring in args[0]:
                response_log_found = True
                break
        self.assertTrue(response_log_found, f"Log message for broker response not found. Expected substring: '{expected_response_substring}'")

    @patch('src.live_trader.execution_handler.logging.getLogger') # More robust patch target
    def test_execute_signal_handles_broker_exception(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        # Re-initialize execution_handler to use the mocked logger
        self.execution_handler = ExecutionHandler(broker_client=self.mock_broker_client)

        market_signal = self.create_sample_signal(OrderSide.BUY, OrderType.MARKET)
        
        exception_message = "Broker connection error"
        self.mock_broker_client.place_order.side_effect = Exception(exception_message)

        self.execution_handler.execute_signal(market_signal)

        mock_logger_instance.error.assert_called_once()
        args, kwargs = mock_logger_instance.error.call_args
        
        # Actual log format: f"Failed to execute signal ID {getattr(signal, 'id', 'N/A')} for {signal.symbol}. Error: {e}"
        expected_log_message_part_1 = f"Failed to execute signal ID {getattr(market_signal, 'id', 'N/A')} for {market_signal.symbol}."
        self.assertIn(expected_log_message_part_1, args[0])
        self.assertTrue(kwargs.get('exc_info')) # ExecutionHandler uses exc_info=True

if __name__ == '__main__':
    unittest.main()

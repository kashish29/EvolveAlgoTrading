import unittest
from unittest.mock import MagicMock, patch, call # Ensure call is imported if used (not explicitly used in provided tests, but good practice)
import logging # Imported for type hinting if needed, but logger patching is by string

# Class to be tested
from src.live_trader.signal_processor import SignalProcessor

# Dependent classes that need mocking
from src.live_trader.execution_handler import ExecutionHandler 

# Models used
from src.core.models import Signal, OrderSide, OrderType 
from datetime import datetime

class TestSignalProcessor(unittest.TestCase):

    def setUp(self):
        self.mock_execution_handler = MagicMock(spec=ExecutionHandler)
        # Create a new mock for each processor instance to avoid shared state across tests if methods are called multiple times
        
        self.sample_signal = Signal(
            timestamp=datetime.now(),
            symbol="TEST_SYM",
            side=OrderSide.BUY, # Ensure this uses the enum member directly
            order_type=OrderType.MARKET, # Ensure this uses the enum member
            quantity=10,
            comment="Test buy signal"
            # id can be omitted if Signal auto-generates or it's optional
        )
        
        self.sample_portfolio_state = {"cash": 100000, "positions": {}}

        # Configure logging to be visible for manual inspection if needed,
        # but tests will mock and assert specific logger calls.
        # logging.basicConfig(level=logging.DEBUG) # Uncomment for debugging tests

    def test_process_signal_no_risk_manager(self):
        # Reset mock for this specific test path
        current_mock_execution_handler = MagicMock(spec=ExecutionHandler)
        signal_processor_no_rm = SignalProcessor(
            execution_handler=current_mock_execution_handler
        )
        signal_processor_no_rm.process_signal(self.sample_signal, self.sample_portfolio_state)
        current_mock_execution_handler.execute_signal.assert_called_once_with(self.sample_signal)

    def test_process_signal_with_risk_manager_trade_valid(self):
        current_mock_execution_handler = MagicMock(spec=ExecutionHandler)
        current_mock_risk_manager = MagicMock()
        current_mock_risk_manager.validate_trade = MagicMock(return_value=True)
        
        signal_processor_with_rm = SignalProcessor(
            execution_handler=current_mock_execution_handler,
            risk_manager=current_mock_risk_manager
        )
        
        signal_processor_with_rm.process_signal(self.sample_signal, self.sample_portfolio_state)
        current_mock_risk_manager.validate_trade.assert_called_once_with(self.sample_signal, self.sample_portfolio_state)
        current_mock_execution_handler.execute_signal.assert_called_once_with(self.sample_signal)

    def test_process_signal_with_risk_manager_trade_invalid(self):
        current_mock_execution_handler = MagicMock(spec=ExecutionHandler)
        current_mock_risk_manager = MagicMock()
        current_mock_risk_manager.validate_trade = MagicMock(return_value=False)

        signal_processor_with_rm = SignalProcessor(
            execution_handler=current_mock_execution_handler,
            risk_manager=current_mock_risk_manager
        )

        signal_processor_with_rm.process_signal(self.sample_signal, self.sample_portfolio_state)
        current_mock_risk_manager.validate_trade.assert_called_once_with(self.sample_signal, self.sample_portfolio_state)
        current_mock_execution_handler.execute_signal.assert_not_called()

    # Patching the logger used within signal_processor.py
    # The SignalProcessor class uses `self.logger = logging.getLogger(self.__class__.__name__)`
    # So, we patch `logging.getLogger` to control the logger instance.
    @patch('logging.getLogger') 
    def test_process_signal_logs_rejection_if_risk_manager_rejects(self, mock_get_logger):
        # Setup mock logger instance that getLogger will return
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        current_mock_execution_handler = MagicMock(spec=ExecutionHandler)
        current_mock_risk_manager = MagicMock()
        current_mock_risk_manager.validate_trade = MagicMock(return_value=False)

        # SignalProcessor will use the mocked logger instance via logging.getLogger
        signal_processor_with_rm = SignalProcessor(
            execution_handler=current_mock_execution_handler,
            risk_manager=current_mock_risk_manager
        )

        signal_processor_with_rm.process_signal(self.sample_signal, self.sample_portfolio_state)
        
        # Check that the warning method of our mock_logger_instance was called
        mock_logger_instance.warning.assert_called_once()
        args, _ = mock_logger_instance.warning.call_args
        # The actual SignalProcessor logs: f"Signal for {signal.symbol}, action {signal.action}, quantity {signal.quantity} was REJECTED by RiskManager."
        # The provided test was: self.assertIn(f"Signal {self.sample_signal} rejected by RiskManager.", args[0])
        # This needs to match the actual log string format from SignalProcessor.
        # SignalProcessor log: `f"Signal for {signal.symbol}, action {signal.action}, quantity {signal.quantity} was REJECTED by RiskManager. Details: {getattr(signal, 'details', {})}"`
        # The test string should be:
        expected_log_part = f"Signal for {self.sample_signal.symbol}, action {self.sample_signal.side.value}, quantity {self.sample_signal.quantity} was REJECTED by RiskManager."
        self.assertIn(expected_log_part, args[0])
        current_mock_execution_handler.execute_signal.assert_not_called()

    @patch('logging.getLogger')
    def test_process_signal_logs_approval_and_forwarding(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        current_mock_execution_handler = MagicMock(spec=ExecutionHandler)
        signal_processor_no_rm = SignalProcessor(
            execution_handler=current_mock_execution_handler
            # No risk_manager
        )

        signal_processor_no_rm.process_signal(self.sample_signal, self.sample_portfolio_state)
        
        # Check that info method was called
        mock_logger_instance.info.assert_called()
        
        found_approval_log = False
        # SignalProcessor logs: `f"Signal for {signal.symbol}, action {signal.action}, quantity {signal.quantity} is now being forwarded to ExecutionHandler. Details: {getattr(signal, 'details', {})}"`
        # The provided test log was: f"Signal {self.sample_signal} approved" and "Forwarding to ExecutionHandler"
        # Let's match the actual log string:
        expected_log_part = f"Signal for {self.sample_signal.symbol}, action {self.sample_signal.side.value}, quantity {self.sample_signal.quantity} is now being forwarded to ExecutionHandler."

        for call_args in mock_logger_instance.info.call_args_list:
            args_list, _ = call_args # call_args is a tuple (args, kwargs)
            if args_list and expected_log_part in args_list[0]:
                found_approval_log = True
                break
        self.assertTrue(found_approval_log, f"Approval log message part '{expected_log_part}' not found in {mock_logger_instance.info.call_args_list}")
        current_mock_execution_handler.execute_signal.assert_called_once_with(self.sample_signal)

    @patch('logging.getLogger')
    def test_process_signal_no_validate_trade_method_on_risk_manager(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        
        current_mock_execution_handler = MagicMock(spec=ExecutionHandler)
        # Risk manager that does not have a callable 'validate_trade' method
        # SignalProcessor checks: `hasattr(self.risk_manager, 'validate_trade') and callable(getattr(self.risk_manager, 'validate_trade'))`
        risk_manager_no_validate_attr = MagicMock()
        del risk_manager_no_validate_attr.validate_trade # Ensure it doesn't have the attribute

        risk_manager_non_callable_validate = MagicMock()
        risk_manager_non_callable_validate.validate_trade = "not a callable method"

        for rm_case in [risk_manager_no_validate_attr, risk_manager_non_callable_validate]:
            # Reset execution handler mock for each case
            current_mock_execution_handler.reset_mock()
            mock_logger_instance.reset_mock()

            processor = SignalProcessor(
                execution_handler=current_mock_execution_handler,
                risk_manager=rm_case
            )
            
            processor.process_signal(self.sample_signal, self.sample_portfolio_state)
            
            mock_logger_instance.warning.assert_called_once()
            args, _ = mock_logger_instance.warning.call_args
            self.assertIn("does not have a callable 'validate_trade' method", args[0])
            current_mock_execution_handler.execute_signal.assert_called_once_with(self.sample_signal)


if __name__ == '__main__':
    unittest.main()

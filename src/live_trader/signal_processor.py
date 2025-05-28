import logging
from typing import TYPE_CHECKING, Optional, Dict

from src.core.models import Signal

if TYPE_CHECKING:
    from src.live_trader.execution_handler import ExecutionHandler # Assuming this is the path
    # from src.risk_management.base_risk_manager import BaseRiskManager # Placeholder for future RiskManager base class

class SignalProcessor:
    def __init__(self, execution_handler: 'ExecutionHandler', risk_manager=None):
        """
        Initializes the SignalProcessor.

        :param execution_handler: Instance of ExecutionHandler to forward approved signals.
        :param risk_manager: Optional instance of a RiskManager.
        """
        self.execution_handler = execution_handler
        self.risk_manager = risk_manager
        
        self.logger = logging.getLogger(self.__class__.__name__)
        # Ensure basic logging configuration if not already set up
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO) # Default level
        
        self.logger.info(f"SignalProcessor initialized. ExecutionHandler: {self.execution_handler}, RiskManager: {self.risk_manager}")

    def process_signal(self, signal: 'Signal', current_portfolio_state: Optional[Dict] = None):
        """
        Processes a trading signal, performing risk checks (if a risk manager is provided)
        and then forwarding the signal to the execution handler.

        :param signal: The Signal object to process.
        :param current_portfolio_state: Optional dictionary representing the current state of the portfolio,
                                         intended for use by the RiskManager.
        """
        self.logger.debug(f"Received signal: {signal}. Portfolio state: {current_portfolio_state}")

        # --- Risk Management ---
        if self.risk_manager:
            self.logger.info(f"Validating signal with RiskManager: {self.risk_manager.__class__.__name__}")
            
            # Check if the risk_manager has a 'validate_trade' method
            validate_trade_method = getattr(self.risk_manager, 'validate_trade', None)
            if callable(validate_trade_method):
                if not validate_trade_method(signal, current_portfolio_state):
                    self.logger.warning(
                        f"Signal for {signal.symbol}, action {signal.action}, quantity {signal.quantity} "
                        f"was REJECTED by RiskManager. Details: {getattr(signal, 'details', {})}"
                    )
                    return  # Stop processing if risk validation fails
            else:
                self.logger.warning(
                    f"Configured RiskManager ({self.risk_manager.__class__.__name__}) "
                    f"does not have a callable 'validate_trade' method. Skipping risk check."
                )
        else:
            self.logger.info("No RiskManager configured. Proceeding without specific risk validation step in SignalProcessor.")

        # --- Forward to Execution Handler ---
        # This block is reached if there's no risk_manager or if risk_manager.validate_trade returned True (or was skipped)
        self.logger.info(
            f"Signal for {signal.symbol}, action {signal.action}, quantity {signal.quantity} "
            f"is now being forwarded to ExecutionHandler. Details: {getattr(signal, 'details', {})}"
        )
        
        try:
            # Check if execution_handler has 'execute_signal' method
            execute_signal_method = getattr(self.execution_handler, 'execute_signal', None)
            if callable(execute_signal_method):
                execute_signal_method(signal)
                self.logger.info(f"Signal {signal} successfully forwarded to and processed by ExecutionHandler.")
            else:
                self.logger.error(
                    f"ExecutionHandler ({self.execution_handler.__class__.__name__}) "
                    f"does not have a callable 'execute_signal' method. Cannot execute signal."
                )
                # Depending on system design, this might warrant raising an error
        except Exception as e:
            self.logger.error(
                f"An error occurred while ExecutionHandler was processing signal: {signal}. Error: {e}",
                exc_info=True # Provides full traceback
            )
            # Decide if this error should be re-raised or handled (e.g., retry, alert)

if __name__ == '__main__':
    # Example Usage (for demonstration and basic testing)
    logging.basicConfig(level=logging.DEBUG) # Set level to DEBUG for detailed example output
    
    # --- Mock Classes for Demonstration ---
    # Using the actual Signal class from src.core.models for type consistency
    # from src.core.models import Signal # Already imported at the top

    class MockExecutionHandler:
        def __init__(self):
            self.logger = logging.getLogger(self.__class__.__name__)
            self.executed_signals = []
            if not self.logger.handlers:
                logging.basicConfig(level=logging.DEBUG) # Ensure logger is configured for mock

        def execute_signal(self, signal: Signal):
            self.logger.info(f"MockExecutionHandler: Executing signal: {signal}")
            self.executed_signals.append(signal)

    class MockRiskManager:
        def __init__(self, approval_mode=True):
            self.logger = logging.getLogger(self.__class__.__name__)
            self.approval_mode = approval_mode
            if not self.logger.handlers:
                logging.basicConfig(level=logging.DEBUG)

        def validate_trade(self, signal: Signal, current_portfolio_state: Optional[Dict] = None) -> bool:
            self.logger.info(
                f"MockRiskManager: Validating signal: {signal} with portfolio state: {current_portfolio_state}"
            )
            if not self.approval_mode:
                self.logger.warning(f"MockRiskManager: Signal {signal} REJECTED based on internal policy.")
                return False
            self.logger.info(f"MockRiskManager: Signal {signal} APPROVED.")
            return True

    # --- Setup and Test Scenarios ---
    
    # Scenario 1: SignalProcessor with RiskManager that approves
    mock_exec_handler_approve = MockExecutionHandler()
    mock_risk_manager_approve = MockRiskManager(approval_mode=True)
    signal_processor_approve = SignalProcessor(
        execution_handler=mock_exec_handler_approve, 
        risk_manager=mock_risk_manager_approve
    )
    
    test_signal_1 = Signal(symbol="AAPL", action="BUY", quantity=100, signal_type="ENTRY", details={"price_target": 155.0})
    print(f"\n--- Testing Scenario 1: Signal with Approving RiskManager ---")
    signal_processor_approve.process_signal(test_signal_1, current_portfolio_state={"cash": 50000})
    assert len(mock_exec_handler_approve.executed_signals) == 1, "Scenario 1 failed: Signal not executed"
    print(f"Execution Handler executed signals: {len(mock_exec_handler_approve.executed_signals)}")


    # Scenario 2: SignalProcessor with RiskManager that rejects
    mock_exec_handler_reject = MockExecutionHandler()
    mock_risk_manager_reject = MockRiskManager(approval_mode=False)
    signal_processor_reject = SignalProcessor(
        execution_handler=mock_exec_handler_reject, 
        risk_manager=mock_risk_manager_reject
    )
    
    test_signal_2 = Signal(symbol="GOOG", action="SELL", quantity=50, signal_type="EXIT", details={"reason": "stop_loss"})
    print(f"\n--- Testing Scenario 2: Signal with Rejecting RiskManager ---")
    signal_processor_reject.process_signal(test_signal_2, current_portfolio_state={"cash": 50000, "positions": {"GOOG": 60}})
    assert len(mock_exec_handler_reject.executed_signals) == 0, "Scenario 2 failed: Signal was executed despite rejection"
    print(f"Execution Handler executed signals: {len(mock_exec_handler_reject.executed_signals)}")


    # Scenario 3: SignalProcessor without RiskManager
    mock_exec_handler_no_rm = MockExecutionHandler()
    signal_processor_no_rm = SignalProcessor(execution_handler=mock_exec_handler_no_rm, risk_manager=None)
    
    test_signal_3 = Signal(symbol="MSFT", action="BUY", quantity=75, signal_type="ENTRY")
    print(f"\n--- Testing Scenario 3: Signal without RiskManager ---")
    signal_processor_no_rm.process_signal(test_signal_3)
    assert len(mock_exec_handler_no_rm.executed_signals) == 1, "Scenario 3 failed: Signal not executed"
    print(f"Execution Handler executed signals: {len(mock_exec_handler_no_rm.executed_signals)}")

    # Scenario 4: SignalProcessor with RiskManager missing 'validate_trade'
    mock_exec_handler_bad_rm = MockExecutionHandler()
    class BadRiskManagerNoMethod: pass # Does not have validate_trade
    signal_processor_bad_rm = SignalProcessor(
        execution_handler=mock_exec_handler_bad_rm, 
        risk_manager=BadRiskManagerNoMethod()
    )
    test_signal_4 = Signal(symbol="TSLA", action="BUY", quantity=10, signal_type="ENTRY")
    print(f"\n--- Testing Scenario 4: Signal with RiskManager missing validate_trade ---")
    signal_processor_bad_rm.process_signal(test_signal_4)
    # Signal should still be processed as the risk check is skipped with a warning
    assert len(mock_exec_handler_bad_rm.executed_signals) == 1, "Scenario 4 failed: Signal not executed"
    print(f"Execution Handler executed signals: {len(mock_exec_handler_bad_rm.executed_signals)}")

    # Scenario 5: SignalProcessor with ExecutionHandler missing 'execute_signal'
    class BadExecutionHandlerNoMethod: pass # Does not have execute_signal
    signal_processor_bad_eh = SignalProcessor(
        execution_handler=BadExecutionHandlerNoMethod(), 
        risk_manager=None
    )
    test_signal_5 = Signal(symbol="AMZN", action="SELL", quantity=20, signal_type="EXIT")
    print(f"\n--- Testing Scenario 5: Signal with ExecutionHandler missing execute_signal ---")
    signal_processor_bad_eh.process_signal(test_signal_5)
    # No signals would be "executed" by the bad handler. The code logs an error.
    # Asserting that no signals were added to a list if BadExecutionHandlerNoMethod had one (it doesn't)
    print("Test complete for Scenario 5 (manual check of logs for error message recommended).")

    print("\nAll SignalProcessor example scenarios run.")

# Ensure a trailing newline
```

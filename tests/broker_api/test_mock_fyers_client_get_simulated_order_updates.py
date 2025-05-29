import unittest
from datetime import datetime, timezone
import uuid

from src.broker_api.mock_fyers_client import MockFyersClient
from src.core.models import Order, Candle
from src.core.enums import OrderType, OrderSide, OrderStatus

class TestMockFyersClientGetSimulatedOrderUpdates(unittest.TestCase):
    """
    Test suite for the get_simulated_order_updates() method of MockFyersClient.
    """

    def setUp(self):
        """
        Set up a new MockFyersClient instance and default parameters for each test.
        """
        self.client = MockFyersClient(initial_cash=100000.0)
        self.symbol_default = "TEST_SYM"
        self.current_time = datetime.now(timezone.utc)

    def _create_order_request(self, symbol: str, order_type: OrderType, side: OrderSide, 
                              quantity: float, price: float = None, trigger_price: float = None,
                              order_id_prefix: str = None) -> Order:
        """Helper method to create a basic order object for placing."""
        order_id_val = f"{order_id_prefix}_{str(uuid.uuid4())}" if order_id_prefix else str(uuid.uuid4())
        return Order(
            order_id=order_id_val, 
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            timestamp=self.current_time
        )

    def _place_limit_order(self, symbol: str, quantity: float = 1.0, price: float = 100.0, 
                           side: OrderSide = OrderSide.BUY, order_id_prefix: str = "limit") -> tuple[str, OrderStatus]:
        """Helper to place a LIMIT order and return its ID and initial status."""
        order_req = self._create_order_request(symbol, OrderType.LIMIT, side, quantity, price=price, order_id_prefix=order_id_prefix)
        return self.client.place_order(order_req)

    # Test Case 1: Rejected Order Update
    def test_rejected_order_update(self):
        order_req_reject = self._create_order_request(self.symbol_default, OrderType.LIMIT, OrderSide.BUY, 1.0, price=None, order_id_prefix="reject")
        self.client.place_order(order_req_reject) # Rejected order

        updates = self.client.get_simulated_order_updates()
        self.assertEqual(len(updates), 1, "Expected one rejected order update.")
        self.assertEqual(updates[0].order_id, order_req_reject.order_id)
        self.assertEqual(updates[0].status, OrderStatus.REJECTED)
        
        self.assertEqual(len(self.client.get_simulated_order_updates()), 0, "Log should be cleared after get.")

    # Test Case 2: Filled Order Update
    def test_filled_order_update(self):
        fill_symbol = "SYMFILL"
        fill_price = 100.0
        order_id_fill, _ = self._place_limit_order(fill_symbol, price=fill_price, order_id_prefix="fill")
        
        fill_candle = Candle(timestamp=self.current_time, open=100.5, high=101.0, low=99.0, close=100.0, volume=100, symbol=fill_symbol)
        self.client.set_current_bar(fill_symbol, fill_candle)
        self.client._process_pending_orders()

        updates = self.client.get_simulated_order_updates()
        self.assertEqual(len(updates), 1, "Expected one filled order update.")
        self.assertEqual(updates[0].order_id, order_id_fill)
        self.assertEqual(updates[0].status, OrderStatus.COMPLETED)
        self.assertIsNotNone(updates[0].executed_price)
        self.assertEqual(updates[0].executed_price, fill_price) # Limit orders fill at limit price
        
        self.assertEqual(len(self.client.get_simulated_order_updates()), 0, "Log should be cleared.")

    # Test Case 3: Cancelled Order Update
    def test_cancelled_order_update(self):
        cancel_symbol = "SYMCANCEL"
        order_id_cancel, _ = self._place_limit_order(cancel_symbol, order_id_prefix="cancel")
        
        self.client.cancel_order(order_id_cancel)
        
        updates = self.client.get_simulated_order_updates()
        self.assertEqual(len(updates), 1, "Expected one cancelled order update.")
        self.assertEqual(updates[0].order_id, order_id_cancel)
        self.assertEqual(updates[0].status, OrderStatus.CANCELLED)
        
        self.assertEqual(len(self.client.get_simulated_order_updates()), 0, "Log should be cleared.")

    # Test Case 4: Multiple Mixed Updates
    def test_multiple_mixed_updates(self):
        # Rejected order
        order_req_reject_mix = self._create_order_request(self.symbol_default, OrderType.LIMIT, OrderSide.SELL, 1.0, price=None, order_id_prefix="mix_reject")
        self.client.place_order(order_req_reject_mix)

        # Filled order
        fill_symbol_mix = "SYMFILL_MIX"
        fill_price_mix = 110.0
        order_id_fill_mix, _ = self._place_limit_order(fill_symbol_mix, price=fill_price_mix, order_id_prefix="mix_fill")
        fill_candle_mix = Candle(timestamp=self.current_time, open=110.5, high=111.0, low=109.0, close=110.0, volume=100, symbol=fill_symbol_mix)
        self.client.set_current_bar(fill_symbol_mix, fill_candle_mix)
        self.client._process_pending_orders()

        # Cancelled order
        cancel_symbol_mix = "SYMCANCEL_MIX"
        order_id_cancel_mix, _ = self._place_limit_order(cancel_symbol_mix, order_id_prefix="mix_cancel")
        self.client.cancel_order(order_id_cancel_mix)

        updates = self.client.get_simulated_order_updates()
        self.assertEqual(len(updates), 3, "Expected three mixed order updates.")
        
        statuses = sorted([o.status for o in updates])
        expected_statuses = sorted([OrderStatus.REJECTED, OrderStatus.COMPLETED, OrderStatus.CANCELLED])
        self.assertEqual(statuses, expected_statuses, "Statuses of mixed updates do not match.")

        order_ids = sorted([o.order_id for o in updates])
        expected_order_ids = sorted([order_req_reject_mix.order_id, order_id_fill_mix, order_id_cancel_mix])
        self.assertEqual(order_ids, expected_order_ids, "Order IDs of mixed updates do not match.")
        
        self.assertEqual(len(self.client.get_simulated_order_updates()), 0, "Log should be cleared.")

    # Test Case 5: No Updates Logged
    def test_no_updates_logged_for_accepted_order(self):
        self._place_limit_order(self.symbol_default, order_id_prefix="no_update") # Order is ACCEPTED, not yet COMPLETED/CANCELLED/REJECTED
        
        updates = self.client.get_simulated_order_updates()
        self.assertEqual(len(updates), 0, "Expected no updates for an order that is only accepted.")

    # Test Case 6: Market Order (Completed) - Behavior Clarification
    def test_market_order_completion_not_in_simulated_updates(self):
        market_symbol = "SYMMARKET"
        market_candle = Candle(timestamp=self.current_time, open=100.0, high=105.0, low=95.0, close=102.0, volume=1000, symbol=market_symbol)
        self.client.set_current_bar(market_symbol, market_candle)
        
        market_order_req = self._create_order_request(market_symbol, OrderType.MARKET, OrderSide.BUY, 1.0, order_id_prefix="market")
        _, status = self.client.place_order(market_order_req)
        self.assertEqual(status, OrderStatus.COMPLETED, "Market order should complete successfully.")
        
        updates = self.client.get_simulated_order_updates()
        # Based on docstring: "Typically, this log is for orders that change state
        # *after* initial placement (e.g., pending orders getting filled, or cancellations)."
        # Successfully filled market orders are synchronous and might not appear here.
        # If a market order *was* rejected (e.g. insufficient funds), it *would* appear.
        self.assertEqual(len(updates), 0, "Successfully completed market order should not appear in simulated updates log.")

if __name__ == '__main__':
    unittest.main()

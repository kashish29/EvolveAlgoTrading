import unittest
from datetime import datetime, timezone
import uuid

from src.broker_api.mock_fyers_client import MockFyersClient
from src.core.models import Order, Candle
from src.core.enums import OrderType, OrderSide, OrderStatus

class TestMockFyersClientModifyCancelOrder(unittest.TestCase):
    """
    Test suite for the modify_order() and cancel_order() methods of MockFyersClient.
    """

    def setUp(self):
        """
        Set up a new MockFyersClient instance and default parameters for each test.
        """
        self.client = MockFyersClient(initial_cash=100000.0)
        self.symbol = "TEST_SYMBOL"
        self.default_quantity = 10.0
        self.default_price = 100.0
        
        # For tests that might involve market execution (e.g., trying to cancel a completed order)
        self.current_candle_time = datetime.now(timezone.utc)
        self.current_candle = Candle(
            timestamp=self.current_candle_time,
            open=95.0,
            high=105.0,
            low=90.0,
            close=102.0, # Used for market order execution
            volume=1000,
            symbol=self.symbol
        )
        self.client.set_current_bar(self.symbol, self.current_candle)


    def _create_base_order_request(self, order_type: OrderType, side: OrderSide, quantity: float, 
                                   price: float = None, trigger_price: float = None, 
                                   order_id: str = None) -> Order:
        """Helper method to create a basic order object for placing."""
        # MockFyersClient is expected to assign an order_id if None is provided.
        # For direct creation for testing internal states, one might be provided.
        return Order(
            id=order_id if order_id else str(uuid.uuid4()), # Changed from order_id to id
            symbol=self.symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            timestamp=datetime.now(timezone.utc)
        )

    def _place_initial_limit_order(self, quantity=None, price=None, side=OrderSide.BUY) -> str:
        """Helper to place a standard LIMIT order and return its ID."""
        qty = quantity if quantity is not None else self.default_quantity
        prc = price if price is not None else self.default_price
        
        order_to_place = self._create_base_order_request(
            order_type=OrderType.LIMIT,
            side=side,
            quantity=qty,
            price=prc
        )
        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.ACCEPTED.value, "Helper failed to place initial LIMIT order.") # Use .value
        self.assertIsNotNone(order_id, "Helper did not receive order_id for initial LIMIT order.")
        return order_id

    # --- Test Cases for modify_order() ---

    def test_modify_order_valid(self):
        """Test modifying a valid, open LIMIT order with new price and quantity."""
        order_id = self._place_initial_limit_order()
        
        new_price = 105.0
        new_quantity = 15.0
        
        success, message = self.client.modify_order(order_id, new_price=new_price, new_quantity=new_quantity)
        
        self.assertTrue(success, f"Modify order failed: {message}")
        self.assertEqual(message, "Order modified successfully") # Removed period
        
        # Verify in open_orders
        self.assertIn(order_id, self.client.open_orders)
        modified_open_order = self.client.open_orders[order_id]
        self.assertEqual(modified_open_order.price, new_price)
        self.assertEqual(modified_open_order.quantity, new_quantity)
        
        # Verify in all_orders
        modified_all_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(modified_all_order)
        self.assertEqual(modified_all_order.price, new_price)
        self.assertEqual(modified_all_order.quantity, new_quantity)
        self.assertEqual(modified_all_order.status, OrderStatus.ACCEPTED.value) # Status should be string from client

    def test_modify_order_non_existent(self):
        """Test modifying an order ID that doesn't exist."""
        non_existent_order_id = "NON_EXISTENT_ID"
        success, message = self.client.modify_order(non_existent_order_id, new_price=110.0)
        
        self.assertFalse(success, "Modifying non-existent order should fail.")
        self.assertEqual(message, "Order not found or not modifiable") # Corrected message

    def test_modify_order_invalid_parameters_zero_quantity(self):
        """Test modifying an order with invalid parameters (e.g., quantity to 0)."""
        order_id = self._place_initial_limit_order()
        
        success, message = self.client.modify_order(order_id, new_quantity=0)
        
        self.assertFalse(success, "Modifying order to zero quantity should fail.")
        self.assertEqual(message, "Invalid quantity for modification")
        
        # Ensure original order is unchanged
        original_order = self.client.open_orders.get(order_id)
        self.assertIsNotNone(original_order)
        self.assertEqual(original_order.quantity, self.default_quantity)

    def test_modify_order_completed_order(self):
        """Test modifying an order that is already COMPLETED (e.g., a MARKET order)."""
        market_order_req = self._create_base_order_request(OrderType.MARKET, OrderSide.BUY, 1)
        # Market order execution relies on current_candle set in setUp()
        order_id, status = self.client.place_order(market_order_req)
        self.assertEqual(status, OrderStatus.COMPLETED.value) # Use .value
        
        success, message = self.client.modify_order(order_id, new_price=100.0) # Attempt modification
        
        self.assertFalse(success, "Modifying a COMPLETED order should fail.")
        self.assertEqual(message, "Order not found or not modifiable") # Corrected message

    def test_modify_order_cancelled_order(self):
        """Test modifying an order that is already CANCELLED."""
        order_id = self._place_initial_limit_order()
        self.client.cancel_order(order_id) # Cancel it first
        
        success, message = self.client.modify_order(order_id, new_price=100.0)
        
        self.assertFalse(success, "Modifying a CANCELLED order should fail.")
        self.assertEqual(message, "Order not found or not modifiable") # Message is correct

    # --- Test Cases for cancel_order() ---

    def test_cancel_order_valid(self):
        """Test cancelling a valid, open LIMIT order."""
        order_id = self._place_initial_limit_order()
        
        success, message = self.client.cancel_order(order_id)
        
        self.assertTrue(success, f"Cancel order failed: {message}")
        self.assertEqual(message, "Order cancelled successfully") 
        
        self.assertNotIn(order_id, self.client.open_orders, "Cancelled order should be removed from open_orders.")
        
        cancelled_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(cancelled_order)
        self.assertEqual(cancelled_order.status, OrderStatus.CANCELLED.value) # Use .value
        
        # Check simulated_order_updates_log
        # Assuming the log stores the order object or its ID and new status
        found_in_update_log = False
        for update in self.client.simulated_order_updates_log: # update is an Order object
            if update.id == order_id and update.status == OrderStatus.CANCELLED.value: # Use .id and .value
                found_in_update_log = True
                break
        self.assertTrue(found_in_update_log, "Cancelled order update not found in simulated_order_updates_log.")

    def test_cancel_order_non_existent(self):
        """Test cancelling an order ID that doesn't exist."""
        non_existent_order_id = "NON_EXISTENT_ID"
        success, message = self.client.cancel_order(non_existent_order_id)
        
        self.assertFalse(success, "Cancelling non-existent order should fail.")
        self.assertEqual(message, "Order not found in open orders") # Corrected message

    def test_cancel_already_cancelled_order(self):
        """Test cancelling an order that has already been cancelled."""
        order_id = self._place_initial_limit_order()
        
        self.client.cancel_order(order_id) # First cancellation
        
        success, message = self.client.cancel_order(order_id) # Attempt second cancellation
        
        self.assertFalse(success, "Cancelling an already CANCELLED order should fail.")
        self.assertEqual(message, "Order not found in open orders") 

    def test_cancel_completed_order(self):
        """Test cancelling an order that is already COMPLETED (e.g., a MARKET order)."""
        market_order_req = self._create_base_order_request(OrderType.MARKET, OrderSide.BUY, 1)
        # Market order execution relies on current_candle set in setUp()
        order_id, status = self.client.place_order(market_order_req)
        self.assertEqual(status, OrderStatus.COMPLETED.value) # Use .value
        
        success, message = self.client.cancel_order(order_id)
        
        self.assertFalse(success, "Cancelling a COMPLETED order should fail.")
        self.assertEqual(message, "Order not found in open orders") 


if __name__ == '__main__':
    unittest.main()

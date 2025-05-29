import unittest
from datetime import datetime, timezone
import uuid

from src.broker_api.mock_fyers_client import MockFyersClient
from src.core.models import Order, Candle, Trade
from src.core.enums import OrderType, OrderSide, OrderStatus

class TestMockFyersClientPlaceOrder(unittest.TestCase):
    """
    Test suite for the place_order() method of MockFyersClient.
    """

    def setUp(self):
        """
        Set up a new MockFyersClient instance and a default candle for each test.
        """
        self.initial_cash = 100000.0
        self.commission_per_trade = 0.01  # Example: 1% commission
        self.slippage_percent = 0.001 # Example: 0.1% slippage
        
        self.client = MockFyersClient(
            initial_cash=self.initial_cash,
            commission_rate=self.commission_per_trade, # Changed to commission_rate
            slippage_percent=self.slippage_percent
        )
        self.symbol = "TEST_SYMBOL"
        
        # Using timezone.utc for datetime objects as it's good practice
        self.current_candle_time = datetime.now(timezone.utc)
        self.current_candle = Candle(
            timestamp=self.current_candle_time,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0, # Market orders will execute based on this 'close' as per typical mock logic
            volume=1000,
            symbol=self.symbol
        )
        # Set the current bar for the symbol for tests that need immediate execution (e.g., MARKET orders)
        self.client.set_current_bar(self.symbol, self.current_candle)

    def _create_base_order(self, order_type: OrderType, side: OrderSide, quantity: float, price: float = None, trigger_price: float = None) -> Order:
        """Helper method to create a basic order object."""
        return Order(
            id=str(uuid.uuid4()), # Ensure 'id' is used as the keyword
            symbol=self.symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            timestamp=datetime.now(timezone.utc)
        )

    # Test Case 1: Valid MARKET Order (BUY)
    def test_place_valid_market_buy_order(self):
        quantity = 10.0
        order_to_place = self._create_base_order(OrderType.MARKET, OrderSide.BUY, quantity)
        
        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.COMPLETED.value, "Market order should be COMPLETED.")
        self.assertIsNotNone(order_id, "Market order should return a valid order_id.")

        # Assert trade log
        self.assertEqual(len(self.client.trade_log), 1, "One trade should be logged.")
        trade = self.client.trade_log[0]
        self.assertEqual(trade.symbol, self.symbol)
        self.assertEqual(trade.quantity, quantity)
        self.assertEqual(trade.side, OrderSide.BUY)
        
        # Expected execution price: current_candle.close * (1 + slippage_percent for BUY)
        expected_price_before_commission = self.current_candle.close * (1 + self.slippage_percent)
        expected_commission = (expected_price_before_commission * quantity) * self.commission_per_trade
        expected_total_cost = (expected_price_before_commission * quantity) + expected_commission

        self.assertAlmostEqual(trade.price, expected_price_before_commission, places=5)
        
        # Assert cash update
        self.assertAlmostEqual(self.client.cash, self.initial_cash - expected_total_cost, places=5,
                             msg="Cash not updated correctly for BUY MARKET order.")

        # Assert positions
        self.assertIn(self.symbol, self.client.positions)
        position = self.client.positions[self.symbol]
        self.assertEqual(position['quantity'], quantity) # Changed to dict access
        self.assertAlmostEqual(position['average_price'], expected_price_before_commission, places=5) # Changed to dict access

        # Assert all_orders
        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(retrieved_order, "Order not found in all_orders.")
        self.assertEqual(retrieved_order.status, OrderStatus.COMPLETED.value)
        self.assertAlmostEqual(retrieved_order.executed_price, expected_price_before_commission, places=5)
        self.assertAlmostEqual(retrieved_order.commission, expected_commission, places=5)
        # executed_quantity is not a field in Order model

    # Test Case 2: Valid LIMIT Order (SELL)
    def test_place_valid_limit_sell_order(self):
        quantity = 5.0
        limit_price = 110.0 # Price above current market, so it shouldn't fill immediately
        order_to_place = self._create_base_order(OrderType.LIMIT, OrderSide.SELL, quantity, price=limit_price)

        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.ACCEPTED.value, "Limit order should be ACCEPTED.")
        self.assertIsNotNone(order_id, "Limit order should return a valid order_id.")

        # Assert open_orders
        self.assertIn(order_id, self.client.open_orders)
        self.assertEqual(self.client.open_orders[order_id].id, order_id) # Changed to .id

        # Assert cash and positions unchanged
        self.assertEqual(self.client.cash, self.initial_cash, "Cash should be unchanged for pending limit order.")
        # Assuming no initial position. If selling, and it was an open short, positions would be checked differently.
        self.assertNotIn(self.symbol, self.client.positions, "Positions should be unchanged for pending limit order.") 

        # Assert all_orders
        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(retrieved_order)
        self.assertEqual(retrieved_order.status, OrderStatus.ACCEPTED.value)
        self.assertEqual(retrieved_order.price, limit_price)
        self.assertIsNone(retrieved_order.executed_price)
        # self.assertEqual(retrieved_order.executed_quantity, 0) # executed_quantity is not a field in Order model

    # Test Case 3: Valid STOP Order (BUY)
    def test_place_valid_stop_buy_order(self):
        quantity = 3.0
        trigger_price = 108.0 # Price above current market
        order_to_place = self._create_base_order(OrderType.STOP, OrderSide.BUY, quantity, trigger_price=trigger_price)

        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.ACCEPTED.value, "Stop order should be ACCEPTED.")
        self.assertIsNotNone(order_id, "Stop order should return a valid order_id.")

        # Assert open_orders
        self.assertIn(order_id, self.client.open_orders)
        self.assertEqual(self.client.open_orders[order_id].id, order_id)
        
        # Assert cash and positions unchanged
        self.assertEqual(self.client.cash, self.initial_cash)
        self.assertNotIn(self.symbol, self.client.positions)

        # Assert all_orders
        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None) # Use iteration
        self.assertIsNotNone(retrieved_order)
        self.assertEqual(retrieved_order.status, OrderStatus.ACCEPTED.value)
        self.assertEqual(retrieved_order.trigger_price, trigger_price)
        self.assertIsNone(retrieved_order.executed_price)
        # executed_quantity is not a field in Order model

    # Test Case 4: Invalid Order (e.g., zero quantity)
    def test_place_invalid_order_zero_quantity(self):
        order_to_place = self._create_base_order(OrderType.MARKET, OrderSide.BUY, quantity=0)
        
        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.REJECTED.value, "Order with zero quantity should be REJECTED.")
        self.assertIsNotNone(order_id, "Rejected order should still return an order_id.")

        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(retrieved_order)
        self.assertEqual(retrieved_order.status, OrderStatus.REJECTED.value)
        self.assertIn("Invalid order parameters", retrieved_order.reject_reason) # Corrected message
        self.assertEqual(len(self.client.trade_log), 0) # No trade should occur

    # Test Case 5: Invalid LIMIT Order (missing price)
    def test_place_invalid_limit_order_missing_price(self):
        order_to_place = self._create_base_order(OrderType.LIMIT, OrderSide.BUY, quantity=1, price=None)

        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.REJECTED.value, "Limit order missing price should be REJECTED.")
        self.assertIsNotNone(order_id)
        
        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(retrieved_order)
        self.assertEqual(retrieved_order.status, OrderStatus.REJECTED.value)
        self.assertIn("Missing price", retrieved_order.reject_reason) # Corrected message
        self.assertEqual(len(self.client.trade_log), 0)

    # Test Case 6: Invalid STOP Order (missing trigger_price)
    def test_place_invalid_stop_order_missing_trigger_price(self):
        order_to_place = self._create_base_order(OrderType.STOP, OrderSide.BUY, quantity=1, trigger_price=None)

        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.REJECTED.value, "Stop order missing trigger price should be REJECTED.")
        self.assertIsNotNone(order_id)

        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(retrieved_order)
        self.assertEqual(retrieved_order.status, OrderStatus.REJECTED.value)
        self.assertIn("Missing trigger_price", retrieved_order.reject_reason) # Corrected message
        self.assertEqual(len(self.client.trade_log), 0)

    # Test Case 7: Insufficient Funds for MARKET order
    def test_place_market_buy_insufficient_funds(self):
        # Try to buy a quantity that would exceed initial_cash
        # candle.close is 102. Slippage 0.1% makes it 102 * 1.001 = 102.102
        # Commission 1% makes total multiplier 1.01
        # Cost per unit = 102.102 * 1.01 = 103.12302
        # With 100k cash, can buy 100000 / 103.12302 = ~969 units
        # So, 1000 units should be insufficient.
        quantity = 1000.0 
        order_to_place = self._create_base_order(OrderType.MARKET, OrderSide.BUY, quantity)

        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.REJECTED.value, "Market order with insufficient funds should be REJECTED.")
        self.assertIsNotNone(order_id)

        retrieved_order = next((o for o in self.client.all_orders if o.id == order_id), None)
        self.assertIsNotNone(retrieved_order)
        self.assertEqual(retrieved_order.status, OrderStatus.REJECTED.value)
        self.assertIn("Insufficient funds", retrieved_order.reject_reason)
        self.assertEqual(len(self.client.trade_log), 0)
        self.assertEqual(self.client.cash, self.initial_cash) # Cash should not change


if __name__ == '__main__':
    unittest.main()

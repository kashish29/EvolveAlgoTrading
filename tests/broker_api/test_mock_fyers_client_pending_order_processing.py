import unittest
from datetime import datetime, timezone
import uuid

from src.broker_api.mock_fyers_client import MockFyersClient
from src.core.models import Order, Candle, Trade
from src.core.enums import OrderType, OrderSide, OrderStatus, Timeframe # Timeframe might not be used directly but good for context

class TestMockFyersClientPendingOrderProcessing(unittest.TestCase):
    """
    Test suite for the _process_pending_orders() method of MockFyersClient,
    focusing on LIMIT and STOP order fill simulation.
    """

    def setUp(self):
        """
        Set up a new MockFyersClient instance and default parameters for each test.
        """
        self.initial_cash = 100000.0
        self.commission_per_trade = 0.01  # 1%
        self.slippage_percent = 0.001 # 0.1%
        
        self.client = MockFyersClient(
            initial_cash=self.initial_cash,
            commission_per_trade=self.commission_per_trade,
            slippage_percent=self.slippage_percent
        )
        self.symbol = "TEST_SYMBOL"
        self.default_quantity = 10.0
        self.current_time = datetime.now(timezone.utc)

    def _create_order_request(self, order_type: OrderType, side: OrderSide, quantity: float, 
                              price: float = None, trigger_price: float = None) -> Order:
        """Helper method to create a basic order object for placing."""
        return Order(
            order_id=str(uuid.uuid4()), 
            symbol=self.symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            timestamp=self.current_time
        )

    def _place_pending_order(self, order_type: OrderType, side: OrderSide, quantity: float, 
                             price: float = None, trigger_price: float = None) -> str:
        """Helper to place a LIMIT or STOP order and return its ID."""
        order_to_place = self._create_order_request(order_type, side, quantity, price, trigger_price)
        order_id, status = self.client.place_order(order_to_place)
        self.assertEqual(status, OrderStatus.ACCEPTED, "Helper failed to place initial pending order.")
        self.assertIsNotNone(order_id, "Helper did not receive order_id for initial pending order.")
        return order_id

    def _set_current_bar_and_process(self, open_price: float, high_price: float, low_price: float, close_price: float):
        """Sets the current bar and calls _process_pending_orders."""
        candle = Candle(
            timestamp=self.current_time, # Ensure timestamp is consistent or incremented if needed
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=1000,
            symbol=self.symbol
        )
        self.client.set_current_bar(self.symbol, candle)
        self.client._process_pending_orders() # Call the method under test

    # --- Test Case 1: LIMIT BUY Order - Fill ---
    def test_limit_buy_order_fill(self):
        limit_price = 100.0
        order_id = self._place_pending_order(OrderType.LIMIT, OrderSide.BUY, self.default_quantity, price=limit_price)
        
        # Bar where low <= limit_price, open > limit_price (fill at limit_price)
        # MockFyersClient logic: fill_price = min(order.price, max(candle.low, candle.open)) for BUY LIMIT if candle.low <= order.price
        # If open=99.5, low=99, limit=100. Fill should be at 100.
        self._set_current_bar_and_process(open_price=99.5, high_price=101.0, low_price=99.0, close_price=100.5)
        
        self.assertNotIn(order_id, self.client.open_orders, "Order should be removed from open_orders after fill.")
        
        filled_order = self.client.all_orders.get(order_id)
        self.assertIsNotNone(filled_order)
        self.assertEqual(filled_order.status, OrderStatus.COMPLETED)
        # Expected fill price for BUY LIMIT is order.price (no slippage on limit price itself)
        expected_fill_price = limit_price 
        self.assertAlmostEqual(filled_order.executed_price, expected_fill_price, places=5)
        
        self.assertEqual(len(self.client.trade_log), 1, "One trade should be logged.")
        trade = self.client.trade_log[0]
        self.assertEqual(trade.order_id, order_id)
        
        expected_commission = (expected_fill_price * self.default_quantity) * self.commission_per_trade
        expected_total_cost = (expected_fill_price * self.default_quantity) + expected_commission
        
        self.assertAlmostEqual(self.client.cash, self.initial_cash - expected_total_cost, places=5)
        self.assertIn(self.symbol, self.client.positions)
        self.assertEqual(self.client.positions[self.symbol].quantity, self.default_quantity)

    # --- Test Case 2: LIMIT BUY Order - No Fill ---
    def test_limit_buy_order_no_fill(self):
        limit_price = 100.0
        order_id = self._place_pending_order(OrderType.LIMIT, OrderSide.BUY, self.default_quantity, price=limit_price)
        
        # Bar where low > limit_price
        self._set_current_bar_and_process(open_price=101.0, high_price=102.0, low_price=100.5, close_price=101.5)
        
        self.assertIn(order_id, self.client.open_orders, "Order should remain in open_orders.")
        original_order = self.client.all_orders.get(order_id)
        self.assertEqual(original_order.status, OrderStatus.ACCEPTED) # Status unchanged

    # --- Test Case 3: STOP SELL Order - Trigger and Fill ---
    def test_stop_sell_order_trigger_and_fill(self):
        trigger_price = 95.0
        # Need an initial BUY position to sell from, or allow short selling
        # For simplicity, let's assume we are flat and short selling is allowed by default in mock
        order_id = self._place_pending_order(OrderType.STOP, OrderSide.SELL, self.default_quantity, trigger_price=trigger_price)
        
        # Bar where low <= trigger_price. Fill price includes slippage.
        # Expected fill: slippage_model(min(open_price, trigger_price), "SELL")
        # If open=94.5, low=94, trigger=95. Fill based on min(94.5, 95) = 94.5
        # Fill price = 94.5 * (1 - slippage_percent for SELL)
        open_p, low_p = 94.5, 94.0
        self._set_current_bar_and_process(open_price=open_p, high_price=96.0, low_price=low_p, close_price=94.2)
        
        self.assertNotIn(order_id, self.client.open_orders)
        filled_order = self.client.all_orders.get(order_id)
        self.assertIsNotNone(filled_order)
        self.assertEqual(filled_order.status, OrderStatus.COMPLETED)
        
        price_before_slippage = min(open_p, trigger_price)
        expected_fill_price = price_before_slippage * (1 - self.slippage_percent)
        self.assertAlmostEqual(filled_order.executed_price, expected_fill_price, places=5)
        
        self.assertEqual(len(self.client.trade_log), 1)
        trade = self.client.trade_log[0]
        self.assertEqual(trade.order_id, order_id)
        
        expected_commission = (expected_fill_price * self.default_quantity) * self.commission_per_trade
        expected_total_value = (expected_fill_price * self.default_quantity) - expected_commission # Cash increases for SELL
        
        self.assertAlmostEqual(self.client.cash, self.initial_cash + expected_total_value, places=5)
        self.assertIn(self.symbol, self.client.positions)
        self.assertEqual(self.client.positions[self.symbol].quantity, -self.default_quantity) # Short position

    # --- Test Case 4: STOP SELL Order - No Trigger ---
    def test_stop_sell_order_no_trigger(self):
        trigger_price = 95.0
        order_id = self._place_pending_order(OrderType.STOP, OrderSide.SELL, self.default_quantity, trigger_price=trigger_price)
        
        # Bar where low > trigger_price
        self._set_current_bar_and_process(open_price=96.0, high_price=97.0, low_price=95.5, close_price=96.5)
        
        self.assertIn(order_id, self.client.open_orders)
        original_order = self.client.all_orders.get(order_id)
        self.assertEqual(original_order.status, OrderStatus.ACCEPTED)

    # --- Test Case 5: LIMIT SELL Order - Fill ---
    def test_limit_sell_order_fill(self):
        limit_price = 105.0
        order_id = self._place_pending_order(OrderType.LIMIT, OrderSide.SELL, self.default_quantity, price=limit_price)
        
        # Bar where high >= limit_price. Fill at limit_price.
        # MockFyersClient logic: fill_price = max(order.price, min(candle.high, candle.open)) for SELL LIMIT if candle.high >= order.price
        # If open=105.5, high=106, limit=105. Fill should be at 105.
        self._set_current_bar_and_process(open_price=105.5, high_price=106.0, low_price=104.0, close_price=105.2)
        
        self.assertNotIn(order_id, self.client.open_orders)
        filled_order = self.client.all_orders.get(order_id)
        self.assertIsNotNone(filled_order)
        self.assertEqual(filled_order.status, OrderStatus.COMPLETED)
        
        expected_fill_price = limit_price # No slippage on limit price itself
        self.assertAlmostEqual(filled_order.executed_price, expected_fill_price, places=5)
        
        self.assertEqual(len(self.client.trade_log), 1)
        expected_commission = (expected_fill_price * self.default_quantity) * self.commission_per_trade
        expected_total_value = (expected_fill_price * self.default_quantity) - expected_commission
        
        self.assertAlmostEqual(self.client.cash, self.initial_cash + expected_total_value, places=5)
        self.assertIn(self.symbol, self.client.positions)
        self.assertEqual(self.client.positions[self.symbol].quantity, -self.default_quantity)

    # --- Test Case 6: LIMIT SELL Order - No Fill ---
    def test_limit_sell_order_no_fill(self):
        limit_price = 105.0
        order_id = self._place_pending_order(OrderType.LIMIT, OrderSide.SELL, self.default_quantity, price=limit_price)
        
        # Bar where high < limit_price
        self._set_current_bar_and_process(open_price=103.0, high_price=104.5, low_price=102.0, close_price=103.5)
        
        self.assertIn(order_id, self.client.open_orders)
        original_order = self.client.all_orders.get(order_id)
        self.assertEqual(original_order.status, OrderStatus.ACCEPTED)

    # --- Test Case 7: STOP BUY Order - Trigger and Fill ---
    def test_stop_buy_order_trigger_and_fill(self):
        trigger_price = 110.0
        order_id = self._place_pending_order(OrderType.STOP, OrderSide.BUY, self.default_quantity, trigger_price=trigger_price)
        
        # Bar where high >= trigger_price. Fill price includes slippage.
        # Expected fill: slippage_model(max(open_price, trigger_price), "BUY")
        # If open=110.5, high=111, trigger=110. Fill based on max(110.5, 110) = 110.5
        # Fill price = 110.5 * (1 + slippage_percent for BUY)
        open_p, high_p = 110.5, 111.0
        self._set_current_bar_and_process(open_price=open_p, high_price=high_p, low_price=109.0, close_price=110.2)
        
        self.assertNotIn(order_id, self.client.open_orders)
        filled_order = self.client.all_orders.get(order_id)
        self.assertIsNotNone(filled_order)
        self.assertEqual(filled_order.status, OrderStatus.COMPLETED)
        
        price_before_slippage = max(open_p, trigger_price)
        expected_fill_price = price_before_slippage * (1 + self.slippage_percent)
        self.assertAlmostEqual(filled_order.executed_price, expected_fill_price, places=5)
        
        self.assertEqual(len(self.client.trade_log), 1)
        expected_commission = (expected_fill_price * self.default_quantity) * self.commission_per_trade
        expected_total_cost = (expected_fill_price * self.default_quantity) + expected_commission
        
        self.assertAlmostEqual(self.client.cash, self.initial_cash - expected_total_cost, places=5)
        self.assertIn(self.symbol, self.client.positions)
        self.assertEqual(self.client.positions[self.symbol].quantity, self.default_quantity)

    # --- Test Case 8: STOP BUY Order - No Trigger ---
    def test_stop_buy_order_no_trigger(self):
        trigger_price = 110.0
        order_id = self._place_pending_order(OrderType.STOP, OrderSide.BUY, self.default_quantity, trigger_price=trigger_price)
        
        # Bar where high < trigger_price
        self._set_current_bar_and_process(open_price=108.0, high_price=109.5, low_price=107.0, close_price=108.5)
        
        self.assertIn(order_id, self.client.open_orders)
        original_order = self.client.all_orders.get(order_id)
        self.assertEqual(original_order.status, OrderStatus.ACCEPTED)

if __name__ == '__main__':
    unittest.main()

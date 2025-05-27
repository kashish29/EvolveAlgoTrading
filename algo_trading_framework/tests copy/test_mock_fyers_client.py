import unittest
import datetime
import logging
import random # For potentially mocking slippage if needed

from src.broker_api.mock_fyers_client import MockFyersClient
from src.core.models import Order, Candle, OrderType, OrderSide, OrderStatus, Timeframe

# Suppress INFO messages from the client during tests
logging.getLogger('src.broker_api.mock_fyers_client').setLevel(logging.WARNING)
# If MockFyersClient uses self.__class__.__name__ for logger:
logging.getLogger('MockFyersClient').setLevel(logging.WARNING)


class TestMockFyersClient(unittest.TestCase):

    def setUp(self):
        self.initial_cash = 100000.0
        self.commission_rate = 0.001
        self.broker = MockFyersClient(
            initial_cash=self.initial_cash,
            commission_rate=self.commission_rate
        )
        self.symbol = "TEST_SYMBOL"
        self.broker.current_time = datetime.datetime(2023, 1, 1, 9, 30, 0)

        # Prepare a default current bar. set_current_bar updates historical_data's last_price.
        default_bar_close = 101.0
        default_bar = Candle(
            timestamp=self.broker.current_time, 
            symbol=self.symbol, 
            open=100.0, high=102.0, low=99.0, close=default_bar_close, 
            volume=1000, timeframe=Timeframe.MINUTE_1
        )
        self.broker.set_current_bar(self.symbol, default_bar)
        # The set_current_bar method in MockFyersClient (Turn 9) also updates 
        # self.broker.historical_data[self.symbol]['last_price'] = bar.close
        # So, market orders will use default_bar_close (101.0) before slippage.

    def test_initial_balance(self):
        self.assertEqual(self.broker.get_balance()['cash'], self.initial_cash)

    def test_place_market_buy_order_successful(self):
        # Current bar close is 101.0 from setUp due to set_current_bar updating historical_data.
        # Let's set a new bar for this test to be explicit.
        bar_time = self.broker.current_time
        current_bar = Candle(timestamp=bar_time, symbol=self.symbol, open=100, high=102, low=99, close=101.0)
        self.broker.set_current_bar(self.symbol, current_bar) # This updates historical_data[symbol]['last_price'] to 101.0

        order_quantity = 10
        order_to_place = Order(id=None, symbol=self.symbol, quantity=order_quantity, side=OrderSide.BUY, order_type=OrderType.MARKET)
        
        order_id, status = self.broker.place_order(order_to_place)
        
        self.assertIsNotNone(order_id)
        self.assertEqual(status, OrderStatus.COMPLETED.value) # Compare with enum's value

        # Fill price for MARKET order is historical_data[symbol]['last_price'] (which is current_bar.close after set_current_bar)
        # then slippage is applied.
        expected_base_fill_price = current_bar.close 
        
        # Check position
        positions = self.broker.get_positions() # Returns list of dicts
        self.assertEqual(len(positions), 1)
        # Assuming positions are dicts as per MockFyersClient
        self.assertEqual(positions[0].get('symbol'), self.symbol)
        self.assertEqual(positions[0].get('quantity'), order_quantity)
        
        # Check executed price (it includes slippage)
        filled_order = next((o for o in self.broker.all_orders if getattr(o, 'id', None) == order_id), None)
        self.assertIsNotNone(filled_order)
        self.assertEqual(getattr(filled_order, 'status'), "COMPLETED") # Mock client sets string status
        
        executed_price = getattr(filled_order, 'executed_price')
        self.assertIsNotNone(executed_price)
        # Assert executed_price is around expected_base_fill_price (e.g., within 0.1% due to slippage model)
        self.assertAlmostEqual(executed_price, expected_base_fill_price, delta=expected_base_fill_price * 0.001) 

        # Check cash deduction
        trade_value = executed_price * order_quantity
        commission = trade_value * self.broker.commission_rate
        self.assertAlmostEqual(self.broker.get_balance()['cash'], self.initial_cash - trade_value - commission)

        # Check trade log
        trade_log = self.broker.get_trade_history() # List of dicts
        self.assertEqual(len(trade_log), 1)
        self.assertEqual(trade_log[0].get('order_id'), order_id)
        self.assertAlmostEqual(trade_log[0].get('price'), executed_price)


    def test_place_limit_buy_order_pending(self):
        order_to_place = Order(id=None, symbol=self.symbol, quantity=5, side=OrderSide.BUY, order_type=OrderType.LIMIT, price=90.0)
        order_id, status_str = self.broker.place_order(order_to_place) # Status is string "ACCEPTED"
        
        self.assertIsNotNone(order_id)
        self.assertEqual(status_str, "ACCEPTED") # Mock client returns string status
        self.assertIn(order_id, self.broker.open_orders)
        self.assertEqual(self.broker.get_balance()['cash'], self.initial_cash)

    def test_process_limit_buy_order_fill(self):
        limit_price = 90.0
        order_quantity = 5
        order_to_place = Order(id=None, symbol=self.symbol, quantity=order_quantity, side=OrderSide.BUY, order_type=OrderType.LIMIT, price=limit_price)
        order_id, _ = self.broker.place_order(order_to_place)
        
        fill_bar_time = self.broker.current_time + datetime.timedelta(minutes=1)
        fill_bar = Candle(timestamp=fill_bar_time, symbol=self.symbol, open=89.0, high=91.0, low=88.0, close=90.0, timeframe=Timeframe.MINUTE_1)
        
        self.broker.set_current_bar(self.symbol, fill_bar)
        self.broker.current_time = fill_bar_time
        self.broker._process_pending_orders()
        
        self.assertNotIn(order_id, self.broker.open_orders)
        
        expected_fill_price = min(fill_bar.open, limit_price)
        trade_value = expected_fill_price * order_quantity
        commission = trade_value * self.broker.commission_rate
        self.assertAlmostEqual(self.broker.get_balance()['cash'], self.initial_cash - trade_value - commission)
        
        filled_order = next((o for o in self.broker.all_orders if getattr(o, 'id', None) == order_id), None)
        self.assertIsNotNone(filled_order)
        self.assertEqual(getattr(filled_order, 'status'), "COMPLETED")
        self.assertAlmostEqual(getattr(filled_order, 'executed_price'), expected_fill_price)

    def test_process_limit_buy_order_no_fill_price_too_high(self):
        order_to_place = Order(id=None, symbol=self.symbol, quantity=5, side=OrderSide.BUY, order_type=OrderType.LIMIT, price=90.0)
        order_id, _ = self.broker.place_order(order_to_place)
        
        non_fill_bar_time = self.broker.current_time + datetime.timedelta(minutes=1)
        non_fill_bar = Candle(timestamp=non_fill_bar_time, symbol=self.symbol, open=91.0, high=92.0, low=90.5, close=91.0, timeframe=Timeframe.MINUTE_1)
        
        self.broker.set_current_bar(self.symbol, non_fill_bar)
        self.broker.current_time = non_fill_bar_time
        self.broker._process_pending_orders()
        
        self.assertIn(order_id, self.broker.open_orders)
        self.assertEqual(self.broker.get_balance()['cash'], self.initial_cash)


    def test_process_stop_buy_order_trigger_and_fill(self):
        trigger_price = 105.0
        order_quantity = 3
        order_to_place = Order(id=None, symbol=self.symbol, quantity=order_quantity, side=OrderSide.BUY, order_type=OrderType.STOP, trigger_price=trigger_price)
        order_id, _ = self.broker.place_order(order_to_place)
        
        trigger_bar_time = self.broker.current_time + datetime.timedelta(minutes=1)
        trigger_bar = Candle(timestamp=trigger_bar_time, symbol=self.symbol, open=104.0, high=106.0, low=103.0, close=105.0, timeframe=Timeframe.MINUTE_1)
        
        self.broker.set_current_bar(self.symbol, trigger_bar)
        self.broker.current_time = trigger_bar_time
        self.broker._process_pending_orders()
        
        self.assertNotIn(order_id, self.broker.open_orders)
        
        filled_order = next((o for o in self.broker.all_orders if getattr(o, 'id', None) == order_id), None)
        self.assertIsNotNone(filled_order)
        self.assertEqual(getattr(filled_order, 'status'), "COMPLETED")
        
        executed_price = getattr(filled_order, 'executed_price')
        self.assertIsNotNone(executed_price)
        
        # Base fill price before slippage
        expected_base_fill_price = max(trigger_bar.open, trigger_price)
        # Assert executed_price is around expected_base_fill_price (e.g., within 0.1% due to slippage model)
        self.assertAlmostEqual(executed_price, expected_base_fill_price, delta=expected_base_fill_price * 0.001)

        trade_value = executed_price * order_quantity
        commission = trade_value * self.broker.commission_rate
        self.assertAlmostEqual(self.broker.get_balance()['cash'], self.initial_cash - trade_value - commission)

    def test_cancel_order_successful(self):
        order_to_place = Order(id=None, symbol=self.symbol, quantity=5, side=OrderSide.BUY, order_type=OrderType.LIMIT, price=90.0)
        order_id, _ = self.broker.place_order(order_to_place)
        
        success, msg = self.broker.cancel_order(order_id)
        self.assertTrue(success)
        self.assertNotIn(order_id, self.broker.open_orders)
        
        cancelled_order = next((o for o in self.broker.all_orders if getattr(o, 'id', None) == order_id), None)
        self.assertIsNotNone(cancelled_order)
        self.assertEqual(getattr(cancelled_order, 'status'), "CANCELLED")

    def test_modify_order_successful(self):
        order_to_place = Order(id=None, symbol=self.symbol, quantity=10, side=OrderSide.BUY, order_type=OrderType.LIMIT, price=90.0)
        order_id, _ = self.broker.place_order(order_to_place)
        
        new_price = 88.0
        new_quantity = 12
        success, msg = self.broker.modify_order(order_id, new_price=new_price, new_quantity=new_quantity)
        self.assertTrue(success)
        
        modified_order_in_open = self.broker.open_orders[order_id]
        self.assertEqual(getattr(modified_order_in_open, 'price'), new_price)
        self.assertEqual(getattr(modified_order_in_open, 'quantity'), new_quantity)
        
        modified_order_in_all = next((o for o in self.broker.all_orders if getattr(o, 'id', None) == order_id), None)
        self.assertIsNotNone(modified_order_in_all)
        self.assertEqual(getattr(modified_order_in_all, 'price'), new_price)
        self.assertEqual(getattr(modified_order_in_all, 'quantity'), new_quantity)
        self.assertIsNotNone(getattr(modified_order_in_all, 'modified_timestamp'))


    def test_get_order_history_and_trade_history(self):
        # Place a market order
        mkt_bar = Candle(timestamp=self.broker.current_time, symbol=self.symbol, open=100, high=102, low=99, close=101.0)
        self.broker.set_current_bar(self.symbol, mkt_bar)
        mkt_order = Order(id=None, symbol=self.symbol, quantity=1, side=OrderSide.BUY, order_type=OrderType.MARKET)
        mkt_order_id, _ = self.broker.place_order(mkt_order)
        
        # Place a limit order that remains pending
        limit_order = Order(id=None, symbol=self.symbol, quantity=2, side=OrderSide.SELL, order_type=OrderType.LIMIT, price=200.0)
        limit_order_id, _ = self.broker.place_order(limit_order)
        
        # Check order history
        all_hist_orders = self.broker.get_order_history() # list of Order objects
        self.assertEqual(len(all_hist_orders), 2)
        
        # Filter by status string as MockFyersClient sets string status on order objects
        completed_orders = self.broker.get_order_history(status="COMPLETED")
        self.assertEqual(len(completed_orders), 1)
        self.assertEqual(getattr(completed_orders[0], 'id'), mkt_order_id)
        
        specific_order_list = self.broker.get_order_history(order_id=limit_order_id)
        self.assertEqual(len(specific_order_list), 1)
        self.assertEqual(getattr(specific_order_list[0], 'status'), "ACCEPTED") # Accepted by broker
        
        # Check trade history (only market order should have a trade)
        trade_hist = self.broker.get_trade_history() # list of trade dicts
        self.assertEqual(len(trade_hist), 1)
        self.assertEqual(trade_hist[0].get('order_id'), mkt_order_id)
        
        trades_for_limit_order = self.broker.get_trade_history(order_id=limit_order_id)
        self.assertEqual(len(trades_for_limit_order), 0)

if __name__ == '__main__':
    unittest.main()

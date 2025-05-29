import unittest
from datetime import datetime, timezone
import uuid

from src.broker_api.mock_fyers_client import MockFyersClient
from src.core.models import Order, Candle, Trade
from src.core.enums import OrderType, OrderSide, OrderStatus

class TestMockFyersClientGetTradeHistory(unittest.TestCase):
    """
    Test suite for the get_trade_history() method of MockFyersClient.
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
        self.symbol1 = "SYM1"
        self.symbol2 = "SYM2"
        self.default_quantity = 10.0
        self.current_time = datetime.now(timezone.utc)

        # Set up a current bar for SYM1 to allow market order execution
        self.sym1_candle = Candle(
            timestamp=self.current_time,
            open=100.0, high=105.0, low=95.0, close=102.0, # close is used for market order fill
            volume=1000, symbol=self.symbol1
        )
        self.client.set_current_bar(self.symbol1, self.sym1_candle)

    def _create_order_request(self, symbol: str, order_type: OrderType, side: OrderSide, 
                              quantity: float, price: float = None, trigger_price: float = None,
                              order_id: str = None) -> Order:
        """Helper method to create a basic order object for placing."""
        return Order(
            order_id=order_id if order_id else str(uuid.uuid4()), 
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            timestamp=self.current_time # Use consistent timestamp for orders in a test
        )

    # --- Test Case 1: Get Full Trade History ---
    def test_get_full_trade_history(self):
        # 1.a.i: Place and execute a BUY MARKET order for 'SYM1'
        market_order_sym1_req = self._create_order_request(self.symbol1, OrderType.MARKET, OrderSide.BUY, self.default_quantity)
        market_order_id_sym1, status_sym1 = self.client.place_order(market_order_sym1_req)
        self.assertEqual(status_sym1, OrderStatus.COMPLETED)
        
        # Store details of the first trade for verification
        trade1_details = self.client.trade_log[0]

        # 1.a.ii: Place a SELL LIMIT order for 'SYM2', then fill it
        limit_price_sym2 = 200.0
        limit_order_sym2_req = self._create_order_request(self.symbol2, OrderType.LIMIT, OrderSide.SELL, 5.0, price=limit_price_sym2)
        limit_order_id_sym2, status_sym2_placed = self.client.place_order(limit_order_sym2_req)
        self.assertEqual(status_sym2_placed, OrderStatus.ACCEPTED)

        # Set current_bar for SYM2 that causes fill and process
        sym2_fill_candle = Candle(
            timestamp=self.current_time, open=201.0, high=202.0, low=199.0, close=200.0, # high >= limit_price
            volume=500, symbol=self.symbol2
        )
        self.client.set_current_bar(self.symbol2, sym2_fill_candle)
        self.client._process_pending_orders()
        
        # Verify SYM2 order is completed
        sym2_order_status = self.client.all_orders[limit_order_id_sym2].status
        self.assertEqual(sym2_order_status, OrderStatus.COMPLETED)
        trade2_details = self.client.trade_log[1] # Second trade in the log

        # 1.b: Call client.get_trade_history()
        trade_history = self.client.get_trade_history()
        
        # 1.c: Assert that the returned list contains two Trade objects
        self.assertEqual(len(trade_history), 2, "Expected two trades in the history.")
        
        # 1.d: Verify details (deep check on one trade for structure, then key fields for both)
        # Trade 1 (SYM1 Market Buy)
        trade_hist_sym1 = next(t for t in trade_history if t.order_id == market_order_id_sym1)
        self.assertEqual(trade_hist_sym1.symbol, self.symbol1)
        self.assertEqual(trade_hist_sym1.side, OrderSide.BUY)
        self.assertEqual(trade_hist_sym1.quantity, self.default_quantity)
        self.assertAlmostEqual(trade_hist_sym1.price, trade1_details.price, places=5) # Price after slippage
        self.assertAlmostEqual(trade_hist_sym1.commission, trade1_details.commission, places=5)
        self.assertIsNone(trade_hist_sym1.pnl, "P&L should be None for individual trades unless explicitly set by a specific logic beyond simple trade logging")

        # Trade 2 (SYM2 Limit Sell)
        trade_hist_sym2 = next(t for t in trade_history if t.order_id == limit_order_id_sym2)
        self.assertEqual(trade_hist_sym2.symbol, self.symbol2)
        self.assertEqual(trade_hist_sym2.side, OrderSide.SELL)
        self.assertEqual(trade_hist_sym2.quantity, 5.0)
        self.assertAlmostEqual(trade_hist_sym2.price, limit_price_sym2, places=5) # Limit orders fill at limit price
        self.assertAlmostEqual(trade_hist_sym2.commission, trade2_details.commission, places=5)
        self.assertIsNone(trade_hist_sym2.pnl)

    # --- Test Case 2: Get Trade History Filtered by Order ID ---
    def test_get_trade_history_filtered_by_order_id(self):
        # Setup similar to Test Case 1
        market_order_sym1_req = self._create_order_request(self.symbol1, OrderType.MARKET, OrderSide.BUY, self.default_quantity)
        market_order_id_sym1, _ = self.client.place_order(market_order_sym1_req)
        
        limit_price_sym2 = 200.0
        limit_order_sym2_req = self._create_order_request(self.symbol2, OrderType.LIMIT, OrderSide.SELL, 5.0, price=limit_price_sym2)
        _, _ = self.client.place_order(limit_order_sym2_req)
        sym2_fill_candle = Candle(timestamp=self.current_time, open=201.0, high=202.0, low=199.0, close=200.0, volume=500, symbol=self.symbol2)
        self.client.set_current_bar(self.symbol2, sym2_fill_candle)
        self.client._process_pending_orders()
        
        # 2.c: Call client.get_trade_history(order_id=market_order_id_sym1)
        filtered_history = self.client.get_trade_history(order_id=market_order_id_sym1)
        
        # 2.d: Assert one Trade object, corresponding to the market order
        self.assertEqual(len(filtered_history), 1, "Expected one trade when filtering by market_order_id_sym1.")
        self.assertEqual(filtered_history[0].order_id, market_order_id_sym1)
        self.assertEqual(filtered_history[0].symbol, self.symbol1)

    # --- Test Case 3: Get Trade History for Non-Existent Order ID ---
    def test_get_trade_history_non_existent_order_id(self):
        # Setup: Place at least one trade so trade_log is not empty
        market_order_sym1_req = self._create_order_request(self.symbol1, OrderType.MARKET, OrderSide.BUY, self.default_quantity)
        _, _ = self.client.place_order(market_order_sym1_req)
        
        # 3.b: Call client.get_trade_history(order_id="non_existent_oid")
        non_existent_history = self.client.get_trade_history(order_id="non_existent_oid")
        
        # 3.c: Assert that the returned list is empty
        self.assertEqual(len(non_existent_history), 0, "Expected empty list for non-existent order_id.")

    # --- Test Case 4: Get Trade History When No Trades Exist ---
    def test_get_trade_history_no_trades_exist(self):
        # 4.a: Instantiate a fresh client (implicitly done by setUp for each test, or create new)
        # For clarity, let's ensure this client instance has no trades
        fresh_client = MockFyersClient(initial_cash=10000.0) # New instance
        
        # 4.b: Call client.get_trade_history()
        empty_history = fresh_client.get_trade_history()
        
        # 4.c: Assert that the returned list is empty
        self.assertEqual(len(empty_history), 0, "Expected empty list when no trades have occurred.")

if __name__ == '__main__':
    unittest.main()

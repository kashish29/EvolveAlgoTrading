import unittest
from src.broker_api.mock_fyers_client import MockFyersClient

class TestMockFyersClientInitialState(unittest.TestCase):
    """
    Test suite for the initial state of MockFyersClient's
    get_balance() and get_positions() methods.
    """

    def test_get_balance_initial_state(self):
        """
        Tests the get_balance() method for its initial state with both
        custom and default initial_cash values.
        """
        # Test with custom initial_cash
        custom_initial_cash = 50000.0
        client_custom = MockFyersClient(initial_cash=custom_initial_cash)
        expected_balance_custom = {
            "cash": custom_initial_cash,
            "margin_available": custom_initial_cash,
            "margin_used": 0.0
        }
        actual_balance_custom = client_custom.get_balance()
        self.assertEqual(actual_balance_custom, expected_balance_custom,
                         "Balance with custom initial cash did not match expected.")

        # Test with default initial_cash (assuming default is 100000.0 as per previous context)
        # If the default changes in MockFyersClient, this test will need adjustment.
        default_initial_cash = 100000.0 
        client_default = MockFyersClient() # Uses default initial_cash
        expected_balance_default = {
            "cash": default_initial_cash,
            "margin_available": default_initial_cash,
            "margin_used": 0.0
        }
        actual_balance_default = client_default.get_balance()
        self.assertEqual(actual_balance_default, expected_balance_default,
                         "Balance with default initial cash did not match expected.")

    def test_get_positions_initial_state(self):
        """
        Tests the get_positions() method for its initial state,
        which should be an empty list.
        """
        client = MockFyersClient()
        initial_positions = client.get_positions()
        self.assertEqual(initial_positions, [],
                         "Initial positions should be an empty list.")
        self.assertIsInstance(initial_positions, list,
                              "Initial positions should be an instance of a list.")

if __name__ == '__main__':
    unittest.main()

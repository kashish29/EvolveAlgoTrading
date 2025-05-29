import unittest
import logging
from src.broker_api.mock_fyers_client import MockFyersClient

class TestMockFyersClientConnection(unittest.TestCase):
    """
    Test suite for MockFyersClient connect and disconnect methods.
    """

    def test_connect_disconnect_flow_and_logs(self):
        """
        Tests the connect() and disconnect() methods, ensuring they execute
        and log appropriate messages.
        """
        client = MockFyersClient()
        
        # The logger name might be 'MockFyersClient' or 'src.broker_api.mock_fyers_client'
        # The logger name is based on self.__class__.__name__ in MockFyersClient
        logger_name_to_test = 'MockFyersClient'

        with self.assertLogs(logger_name_to_test, level='INFO') as cm:
            # Test connect()
            try:
                client.connect()
            except Exception as e:
                self.fail(f"client.connect() raised an exception unexpectedly: {e}")
            
            # Test disconnect()
            try:
                client.disconnect()
            except Exception as e:
                self.fail(f"client.disconnect() raised an exception unexpectedly: {e}")

        # Verify log messages
        self.assertTrue(any(f"INFO:{logger_name_to_test}:MockFyersClient connected." in log_msg for log_msg in cm.output))
        self.assertTrue(any(f"INFO:{logger_name_to_test}:MockFyersClient disconnected." in log_msg for log_msg in cm.output))
        
        # Check connection status if available (assuming an is_connected attribute or similar)
        # This part is speculative as the original class definition isn't provided
        if hasattr(client, 'is_connected'):
            self.assertFalse(client.is_connected, "Client should be disconnected after disconnect call.")

if __name__ == '__main__':
    unittest.main()

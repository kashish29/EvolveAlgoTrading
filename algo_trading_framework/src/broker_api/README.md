# Broker API Module

This module is responsible for all interactions with the trading broker. Its primary role is to abstract the specifics of a particular broker's API, providing a consistent interface for the rest of the trading framework.

## Current Implementation: `MockFyersClient`

The current implementation within `fyers_client.py` is a **`MockFyersClient`**. This client **does not connect to the actual Fyers API**. Instead, it simulates the behavior of the Fyers API V3 for development and testing purposes.

### Key Features of `MockFyersClient`:
- Simulates connection and authentication.
- Returns pre-generated or randomly generated mock historical data (candlesticks).
- Simulates order placement (MARKET, LIMIT) and returns mock order IDs.
- Provides mock order status updates, with a chance for LIMIT orders to be "filled" over time.
- Tracks and returns mock portfolio positions based on simulated trades.
- No actual financial transactions occur.

This mock client is crucial for:
- Developing strategy logic without needing live API keys or risking capital.
- Unit and integration testing of components that rely on broker interaction (e.g., data handler, execution handler, backtester).
- Running the system in an offline mode for demonstrations or debugging.

**Future Development:**
- A `FyersClient` that interacts with the live Fyers API V3 will be developed.
- An abstract `BaseBrokerClient` could be introduced if support for multiple brokers is desired in the future, ensuring all clients adhere to a common interface.

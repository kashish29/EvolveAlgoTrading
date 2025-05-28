# Broker API Module (`src/broker_api/`)

This module is responsible for all interactions with trading brokers. Its primary role is to abstract the specifics of a particular broker's API, providing a consistent interface for the rest of the trading framework to place orders, fetch data, and manage account information.

## Components:

### 1. `base_broker_client.py` - `BaseBrokerClient` (Abstract Base Class)

-   **Purpose**: Defines the abstract `BaseBrokerClient` class, which serves as a standardized interface for all concrete broker implementations within the framework.
-   **Interface**: It specifies a set of common methods that any broker client must implement. These methods typically include:
    -   `connect()`: To establish a connection with the broker.
    -   `get_historical_data(symbol, timeframe, from_date, to_date)`: To fetch historical candlestick data.
    -   `get_live_market_data(symbol)`: To get real-time market data (if supported).
    -   `place_order(order: Order)`: To submit new orders (e.g., MARKET, LIMIT, STOPLOSS).
    -   `modify_order(order_id, new_params)`: To modify existing pending orders.
    -   `cancel_order(order_id)`: To cancel pending orders.
    -   `get_order_status(order_id)`: To check the status of an order.
    -   `get_positions()`: To retrieve current open positions in the portfolio.
    -   `get_holdings()`: To retrieve long-term holdings.
    -   `get_balance()`: To get account balance and margin information.
    -   `get_profile()`: To get user profile details.
-   **Importance**: By requiring all specific broker clients (like `FyersClient` or `MockFyersClient`) to inherit from and implement this base class, the rest of the framework can interact with different brokers in a uniform way, promoting modularity and ease of switching between brokers.

### 2. `mock_fyers_client.py` - `MockFyersClient`

-   **Purpose**: Provides a `MockFyersClient` class that simulates the behavior of a Fyers trading broker. This is essential for development, testing, and offline demonstrations without requiring a live broker connection or API keys.
-   **Role**:
    -   Allows developers to build and test strategies and other framework components (like the `Backtester` or `FitnessEvaluator`) without needing live API credentials or risking capital.
    -   Enables unit and integration testing by providing predictable responses for various broker interactions.
-   **Capabilities**:
    -   **Connection Simulation**: Simulates connection and authentication steps.
    -   **Data Provision**: Can be set up to return pre-defined or randomly generated mock historical data (candlesticks) and simulated live data.
    -   **Order Simulation**:
        -   Accepts order placements (MARKET, LIMIT, STOPLOSS etc.).
        -   Returns mock order IDs and simulates order status updates (e.g., PENDING, EXECUTED, CANCELED, REJECTED).
        -   For LIMIT orders, it can simulate partial or full fills based on mock market conditions or timed delays.
    -   **Portfolio Management**:
        -   Maintains a mock portfolio, tracking cash, open positions, and holdings based on simulated trades.
        -   Calculates notional profit/loss for open positions.
    -   **No Real Transactions**: Critically, no actual financial transactions occur, and no communication with any external broker API happens.

### 3. `fyers_client.py` - `FyersClient`

-   **Purpose**: This file contains (or is intended for) the `FyersClient` class, which is a concrete implementation of `BaseBrokerClient` designed to interact with the **actual Fyers Trading API (V3)**.
-   **Role**:
    -   Enables the framework to connect to a live Fyers trading account.
    -   Allows for fetching real-time market data, placing live trades, and managing a real trading portfolio.
-   **Functionality**:
    -   Implements all methods defined in `BaseBrokerClient` by making corresponding calls to the Fyers API.
    -   Handles API authentication, request formatting, response parsing, and error management specific to the Fyers API.
    -   This client is used when the framework is intended for live trading or for backtesting with historical data fetched directly from Fyers.

By structuring the module this way, strategies and other parts of the system can be developed and tested against the `MockFyersClient` and then seamlessly switched to the `FyersClient` (or another broker-specific client) for live deployment with minimal code changes.

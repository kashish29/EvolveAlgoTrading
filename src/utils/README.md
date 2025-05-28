# Utilities Module (`src/utils/`)

This module provides common utility functions and classes used across various parts of the Algorithmic Trading Framework. These utilities help in standardizing common tasks like configuration management, logging, and date/time operations.

## Key Files:

### 1. `config_loader.py`

-   **Purpose**: This file is responsible for loading configuration settings from external files (e.g., YAML, JSON, or INI files).
-   **Functionality**:
    -   Provides functions or classes to read configuration files from specified paths.
    -   Makes configuration parameters easily accessible to other modules in the framework.
    -   May include mechanisms for validating configuration schemas or providing default values.
-   **Usage**: Typically used at the startup of applications (e.g., `main.py`, backtester, live trader) to load settings for database connections, API keys, strategy parameters, file paths, etc.

### 2. `datetime_utils.py`

-   **Purpose**: Contains utility functions for common date and time manipulations that are frequently needed in financial applications and trading algorithms.
-   **Functionality**: May include helper functions for:
    -   Parsing date/time strings into datetime objects.
    -   Formatting datetime objects into specific string representations.
    -   Performing timezone conversions (e.g., UTC to local time and vice-versa).
    -   Calculating time differences or adding/subtracting time deltas.
    -   Handling market-specific time considerations (e.g., checking if markets are open, aligning timestamps to market hours, though this might also be part of a market data utility).
    -   Generating sequences of dates or times for analysis or scheduling.

### 3. `logger.py`

-   **Purpose**: This file is responsible for setting up and providing a standardized logging mechanism for the entire framework.
-   **Functionality**:
    -   Initializes a logger instance (often a global or easily accessible one) using Python's built-in `logging` module.
    -   Configures the logger with desired settings, such as:
        -   Log level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).
        -   Log format (e.g., including timestamp, module name, log level, message).
        -   Log handlers (e.g., logging to console, logging to a file, rotating log files).
    -   Provides an easy way for other modules to obtain and use this configured logger instance, ensuring consistent log output across the application.
-   **Usage**: All other modules in the framework should use the logger provided by this utility to record events, errors, and informational messages, aiding in debugging, monitoring, and auditing.

Using these utilities helps maintain consistency, reduces code duplication, and simplifies common operational tasks within the framework.

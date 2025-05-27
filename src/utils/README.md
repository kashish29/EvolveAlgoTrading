# Utilities Module (`src/utils/`)

This module provides common utility functions and classes used across the Algorithmic Trading Framework.

## `config_loader.py`
- **`load_config(config_path)`:** A function to load configurations from YAML files. It handles file reading and parsing, raising appropriate errors if issues occur. This is used to load strategy parameters, system settings, and API credentials.

## `logger.py`
- **`get_logger(name, log_level, ...)`:** A function to set up and retrieve Python `logging` instances. It allows for consistent log formatting and output handling (e.g., to console and/or log files) across different modules of the framework. This helps in debugging and monitoring the application.

## `datetime_utils.py`
- Contains utility functions for common date and time operations, such as:
  - Getting the current UTC timestamp (`get_current_utc_timestamp`).
  - Formatting datetime objects into strings (`format_timestamp`).
- This can be expanded with functions for timezone conversions, market hours checks, or other time-related calculations relevant to trading.

---
These utilities aim to centralize common functionalities, reduce code duplication, and improve the overall maintainability of the framework.

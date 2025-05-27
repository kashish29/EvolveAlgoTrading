# Testing (`tests/`)

This directory contains all the unit and integration tests for the Algorithmic Trading Framework. Tests are crucial for ensuring the reliability, correctness, and maintainability of the codebase.

## Testing Framework
We use Python's built-in `unittest` module as the primary testing framework.

## Structure
The structure of the `tests/` directory mirrors the `src/` directory. For example, tests for `src/core/models.py` will be located in `tests/core/test_models.py`.

## Running Tests
Currently, tests can be run individually by executing the specific test file (e.g., `python -m unittest tests.core.test_models`).

For running all tests, you can navigate to the root directory of the project (`algo_trading_framework/../`) and run:
`python -m unittest discover tests`

Or from within the `algo_trading_framework` directory:
`python -m unittest discover .` (if your `__init__.py` files are set up to make `tests` a discoverable package, or more reliably specify the start directory `python -m unittest discover -s tests -p 'test_*.py'`)


## Coverage
Test coverage should be increased over time to cover all critical components and logic. (Coverage tools like `coverage.py` can be integrated later).

## Types of Tests
- **Unit Tests:** Focus on testing individual functions, methods, or classes in isolation. Mocking is used to isolate dependencies.
- **Integration Tests:** (To be added later) Will test the interaction between different components of the framework.

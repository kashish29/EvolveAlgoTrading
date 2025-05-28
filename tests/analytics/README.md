# Analytics Tests (`tests/analytics`)

This directory contains unit tests for the Analytics module, primarily focusing on the `PerformanceReporter` class.

## `test_performance_reporter.py`

This file includes a comprehensive suite of unit tests for `src/analytics/performance_reporter.py`.

### Testing Approach:

*   **Mocking**: External libraries such as `quantstats` (for report generation and statistical functions) and `matplotlib.pyplot` (for plotting) are mocked using `unittest.mock`. This isolates the logic within `PerformanceReporter` for testing.
*   **Scenario Coverage**: Tests cover various scenarios, including:
    *   Initialization with different types of equity curves (valid, non-DatetimeIndex, empty).
    *   Correct calculation of daily percentage returns from an equity curve.
    *   Verification of calls to `quantstats.reports.html` with correct arguments for report generation.
    *   Validation of key performance metrics calculated by `calculate_key_metrics` against expected values for different trade and equity curve profiles (profitable, losing, no trades, all wins, all losses).
    *   Verification of calls to plotting functions (`plot_equity_curve`, `plot_drawdown_underwater`) with appropriate arguments, checking handling of `show` and `output_path` parameters.
*   **Data Fixtures**: Sample `equity_curve` (Pandas Series) and `trades` (Pandas DataFrame) are generated as test fixtures to provide consistent inputs for test cases.
*   **Focus**: The tests aim to verify the internal logic of `PerformanceReporter` (data processing, calls to external libraries, metric calculations) rather than the correctness of the external libraries themselves.

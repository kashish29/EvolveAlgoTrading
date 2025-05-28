# Analytics Module (`src/analytics`)

This module is responsible for providing detailed performance analysis and reporting for trading strategies.

## Core Component: `PerformanceReporter`

The primary class in this module is `PerformanceReporter` (located in `performance_reporter.py`).

### Purpose
`PerformanceReporter` takes raw backtest outputs (trade history and equity curve) and generates comprehensive performance reports, key metrics, and visualizations.

### Key Methods and Functionalities:

*   **`__init__(self, trades: pd.DataFrame, equity_curve: pd.Series, benchmark_returns: pd.Series = None, config: dict = None)`**:
    *   Initializes the reporter with trade data (Pandas DataFrame), portfolio equity curve (Pandas Series), optional benchmark returns (Pandas Series of daily percentage returns), and an optional configuration dictionary.
    *   Internally calculates daily percentage returns from the equity curve.

*   **`_calculate_daily_returns(self) -> pd.Series`**:
    *   A helper method that converts the time-series portfolio equity values into a Series of daily percentage returns. It handles resampling to daily frequency.

*   **`generate_quantstats_report(self, output_path: str = "report.html", title: str = "Strategy Performance")`**:
    *   Generates a detailed HTML performance report using the `quantstats` library.
    *   The report includes a wide array of metrics, charts, and comparisons against a benchmark if provided.

*   **`calculate_key_metrics(self) -> dict`**:
    *   Calculates and returns a dictionary of critical performance metrics. This includes:
        *   Return-based metrics (e.g., Total Return, CAGR, Sharpe Ratio, Sortino Ratio, Max Drawdown, Calmar Ratio) derived from daily returns using `quantstats.stats`.
        *   Trade-based metrics (e.g., Win Rate, Profit Factor, Average Winning Trade PnL, Average Losing Trade PnL, Total Trades) derived from the input `trades` DataFrame.

*   **`plot_equity_curve(self, output_path: str = None, show: bool = True)`**:
    *   Plots the strategy's equity curve using `matplotlib.pyplot`.
    *   If benchmark returns are provided, it synthesizes and plots a comparable benchmark equity curve on the same chart.
    *   Can save the plot to a file and/or display it.

*   **`plot_drawdown_underwater(self, output_path: str = None, show: bool = True)`**:
    *   Plots the underwater drawdown chart (portfolio value relative to previous highs) using `quantstats.plots.drawdown` or `matplotlib`.
    *   Can save the plot to a file and/or display it.

*   **`plot_trades_on_price_chart(self, symbol: str, price_data: pd.DataFrame, output_path: str = None, show: bool = True)` (Optional)**:
    *   An advanced optional method to overlay trade markers (buy/sell points) onto a price chart for a specific symbol. (Note: This was part of the initial issue but not implemented in the first pass).

### Primary Libraries Used:

*   **QuantStats**: For generating sophisticated statistical reports and some plotting functionalities.
*   **Pandas**: For data manipulation, especially for handling trades and equity curves.
*   **Matplotlib**: For generating plots like the equity curve.
*   **Plotly (Optional)**: Can be used for interactive charts if `PerformanceReporter` is extended.

### Integration:

*   **`BacktesterEngine`**: Uses `PerformanceReporter` to automatically generate an HTML report and equity curve plot after a backtest run if the `generate_analytics_report` flag is enabled.
*   **`FitnessEvaluator`**: Uses `PerformanceReporter.calculate_key_metrics()` to obtain a comprehensive set of metrics for evaluating the fitness of strategies in the Strategy Lab.

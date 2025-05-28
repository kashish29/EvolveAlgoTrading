import pandas as pd
import quantstats
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)
import numpy as np # Import numpy for np.random used in example

class PerformanceReporter:
    def __init__(self, trades: pd.DataFrame, equity_curve: pd.Series, benchmark_returns: pd.Series = None, config: dict = None):
        self.trades = trades
        self.equity_curve = equity_curve 
        self.benchmark_returns = benchmark_returns # Expected to be daily percentage returns
        self.config = config if config is not None else {}

        if not isinstance(self.equity_curve.index, pd.DatetimeIndex):
            try:
                self.equity_curve.index = pd.to_datetime(self.equity_curve.index)
                logger.debug("PerformanceReporter: Equity curve index converted to DatetimeIndex.")
            except Exception as e:
                logger.warning(f"PerformanceReporter: Warning - Failed to convert equity_curve index to DatetimeIndex: {e}. Calculations may fail.")

        if self.benchmark_returns is not None and not isinstance(self.benchmark_returns.index, pd.DatetimeIndex):
            try:
                self.benchmark_returns.index = pd.to_datetime(self.benchmark_returns.index)
                logger.debug("PerformanceReporter: Benchmark returns index converted to DatetimeIndex.")
            except Exception as e:
                logger.warning(f"PerformanceReporter: Warning - Failed to convert benchmark_returns index to DatetimeIndex: {e}. Calculations may fail.")
        
        self.daily_returns = self._calculate_daily_returns()

    def _calculate_daily_returns(self) -> pd.Series:
        if self.equity_curve is None or self.equity_curve.empty:
            logger.warning("PerformanceReporter: Warning - Equity curve is empty or None. Cannot calculate daily returns.")
            return pd.Series(dtype=float)

        if not isinstance(self.equity_curve.index, pd.DatetimeIndex):
            logger.error("PerformanceReporter: Error - Equity curve index is not DatetimeIndex. Cannot resample for daily returns.")
            return pd.Series(dtype=float)

        # Resample to daily frequency, taking the last value of each day
        daily_equity = self.equity_curve.resample('D').last()
        
        # Calculate daily percentage change
        daily_returns = daily_equity.pct_change().dropna()
        
        # Ensure the index is just date for quantstats compatibility
        daily_returns.index = daily_returns.index.normalize() 
        
        return daily_returns

    def generate_quantstats_report(self, output_path: str = "report.html", title: str = "Strategy Performance"):
        if self.daily_returns.empty:
            logger.warning("PerformanceReporter: Daily returns are empty. Cannot generate QuantStats report.")
            return

        qs_returns = self.daily_returns.copy()
        # QuantStats expects returns as Series with DatetimeIndex (just date part)
        if not isinstance(qs_returns.index, pd.DatetimeIndex):
             qs_returns.index = pd.to_datetime(qs_returns.index)
        qs_returns.index = qs_returns.index.normalize()


        qs_benchmark = None
        if self.benchmark_returns is not None and not self.benchmark_returns.empty:
            qs_benchmark = self.benchmark_returns.copy()
            if not isinstance(qs_benchmark.index, pd.DatetimeIndex):
                qs_benchmark.index = pd.to_datetime(qs_benchmark.index)
            qs_benchmark.index = qs_benchmark.index.normalize()
            
            # Align benchmark with returns. quantstats.utils.make_portfolio can help here.
            # It ensures both series cover the same period and are suitable for comparison.
            # This might alter the series slightly (e.g., by forward-filling missing dates or trimming).
            # For reporting, it's generally fine.
            try:
                # make_portfolio returns a DataFrame if benchmark is provided, or Series if not.
                # We need to handle this. If it's a DataFrame, strategy returns are typically the first column.
                aligned_data = quantstats.utils.make_portfolio(qs_returns, benchmark=qs_benchmark, period="daily")
                if isinstance(aligned_data, pd.DataFrame) and not aligned_data.empty:
                    qs_returns = aligned_data.iloc[:, 0] # First column is usually strategy returns
                    if aligned_data.shape[1] > 1:
                        qs_benchmark = aligned_data.iloc[:, 1] # Second column is benchmark
                    else: # Should not happen if benchmark was passed and valid
                        qs_benchmark = None 
                elif isinstance(aligned_data, pd.Series): # Only returns were processed
                    qs_returns = aligned_data
                    qs_benchmark = None # Reset benchmark if make_portfolio didn't include it
                logger.debug("PerformanceReporter: Aligned returns and benchmark for QuantStats report.")
            except Exception as e:
                logger.warning(f"PerformanceReporter: Warning - Could not align returns and benchmark via quantstats.utils.make_portfolio: {e}. Proceeding with original series.")
        try:
            quantstats.reports.html(qs_returns, benchmark=qs_benchmark, output=output_path, title=title, compounded=True)
            logger.info(f"PerformanceReporter: QuantStats report generated at {output_path}")
        except Exception as e:
            logger.error(f"PerformanceReporter: Error generating QuantStats report: {e}")

    def calculate_key_metrics(self) -> dict:
        metrics = {}

        if not self.daily_returns.empty:
            qs_returns = self.daily_returns.copy()
            if not isinstance(qs_returns.index, pd.DatetimeIndex):
                qs_returns.index = pd.to_datetime(qs_returns.index)
            qs_returns.index = qs_returns.index.normalize()

            metrics["Total Return [%]"] = quantstats.stats.comp(qs_returns) * 100
            metrics["CAGR [%]"] = quantstats.stats.cagr(qs_returns) * 100
            metrics["Sharpe Ratio"] = quantstats.stats.sharpe(qs_returns)
            metrics["Sortino Ratio"] = quantstats.stats.sortino(qs_returns) # prepare_returns=False as we already have daily
            metrics["Max Drawdown [%]"] = quantstats.stats.max_drawdown(qs_returns) * 100 
            metrics["Calmar Ratio"] = quantstats.stats.calmar(qs_returns)
            # metrics["Volatility (Ann.) [%]"] = quantstats.stats.volatility(qs_returns, annualize=True, prepare_returns=False) * 100
            # metrics["Skew"] = quantstats.stats.skew(qs_returns, prepare_returns=False)
            # metrics["Kurtosis"] = quantstats.stats.kurtosis(qs_returns, prepare_returns=False)
        else:
            logger.warning("PerformanceReporter: Daily returns are empty. Cannot calculate most performance metrics.")
            metrics["Total Return [%]"] = 0.0
            metrics["CAGR [%]"] = 0.0
            metrics["Sharpe Ratio"] = 0.0
            metrics["Sortino Ratio"] = 0.0
            metrics["Max Drawdown [%]"] = 0.0
            metrics["Calmar Ratio"] = 0.0

        if self.trades is not None and not self.trades.empty and 'pnl' in self.trades.columns:
            total_trades = len(self.trades)
            winning_trades_df = self.trades[self.trades['pnl'] > 0]
            losing_trades_df = self.trades[self.trades['pnl'] < 0]

            num_winning_trades = len(winning_trades_df)
            num_losing_trades = len(losing_trades_df)

            metrics["Total Trades"] = total_trades
            metrics["Win Rate [%]"] = (num_winning_trades / total_trades) * 100 if total_trades > 0 else 0

            gross_profits = winning_trades_df['pnl'].sum()
            gross_losses = abs(losing_trades_df['pnl'].sum())

            metrics["Profit Factor"] = gross_profits / gross_losses if gross_losses > 0 else float('inf') if gross_profits > 0 else 1.0 # Handle division by zero

            metrics["Avg Winning Trade PnL"] = winning_trades_df['pnl'].mean() if num_winning_trades > 0 else 0
            metrics["Avg Losing Trade PnL"] = losing_trades_df['pnl'].mean() if num_losing_trades > 0 else 0
        else:
            logger.warning("PerformanceReporter: Trades data is missing or 'pnl' column not found. Cannot calculate trade-based metrics.")
            metrics["Total Trades"] = 0
            metrics["Win Rate [%]"] = 0
            metrics["Profit Factor"] = 0
            metrics["Avg Winning Trade PnL"] = 0
            metrics["Avg Losing Trade PnL"] = 0
            
        return metrics

    def plot_equity_curve(self, output_path: str = None, show: bool = True):
        logger.info(f"plot_equity_curve called with output_path='{output_path}', show={show}")
        if self.equity_curve is None or self.equity_curve.empty:
            logger.warning("PerformanceReporter: Equity curve is empty. Cannot plot.")
            return

        fig, ax = plt.subplots(figsize=self.config.get('plot_figsize', (12, 8)))
        ax.plot(self.equity_curve.index, self.equity_curve, label="Strategy Equity")
        
        if self.benchmark_returns is not None and not self.benchmark_returns.empty:
            # Ensure benchmark_returns has DatetimeIndex
            benchmark_plot_returns = self.benchmark_returns.copy()
            if not isinstance(benchmark_plot_returns.index, pd.DatetimeIndex):
                benchmark_plot_returns.index = pd.to_datetime(benchmark_plot_returns.index)
            benchmark_plot_returns.index = benchmark_plot_returns.index.normalize()

            # Align benchmark returns to the equity curve's timeline
            # Get the first equity value and date
            first_equity_date = self.equity_curve.index.min()
            initial_equity = self.equity_curve.loc[first_equity_date]

            # Filter benchmark returns from the strategy's start date
            benchmark_plot_returns = benchmark_plot_returns[benchmark_plot_returns.index >= first_equity_date]
            
            if not benchmark_plot_returns.empty:
                # Calculate benchmark equity curve: (1 + daily_return).cumprod() * initial_equity
                # The first benchmark return should ideally be 0 on first_equity_date
                # or the calculation needs to be adjusted.
                # If benchmark_plot_returns starts on first_equity_date, its first value is the return for that day.
                
                # Create a new series for benchmark equity starting at initial_equity on first_equity_date
                benchmark_equity_curve = pd.Series(index=benchmark_plot_returns.index, dtype=float)
                
                # If benchmark_plot_returns.index[0] == first_equity_date, the first calculated point will be
                # initial_equity * (1 + benchmark_plot_returns.iloc[0])
                # We want the benchmark to visually start at the same point 'initial_equity'.
                # So, we can prepend initial_equity and then compute cumulative product on returns from the next day.

                # Simpler: create a series of benchmark values starting with initial_equity
                # then apply returns.
                temp_benchmark_equity = initial_equity * (1 + benchmark_plot_returns).cumprod()
                
                # If the benchmark series doesn't start exactly on first_equity_date but later,
                # then prepend initial_equity up to the day before benchmark starts.
                # However, quantstats.utils.make_portfolio used in reporting usually handles alignment.
                # For plotting, explicit alignment is good.

                # Reindex benchmark equity to match strategy equity for plotting, then fill gaps
                # This ensures they are plotted over the same range.
                
                # Let's use a common index starting from first_equity_date
                common_index = self.equity_curve.index[self.equity_curve.index >= first_equity_date]
                
                # Create the benchmark equity curve
                # Start with initial_equity, then apply benchmark returns
                # Ensure benchmark_plot_returns aligns with common_index
                aligned_benchmark_returns = benchmark_plot_returns.reindex(common_index, fill_value=0.0)
                
                # Calculate cumulative product of (1 + returns)
                cumulative_benchmark_returns = (1 + aligned_benchmark_returns).cumprod()
                benchmark_equity_display = initial_equity * cumulative_benchmark_returns
                
                # The very first point of benchmark_equity_display should be initial_equity.
                # If aligned_benchmark_returns[0] was for first_equity_date, then
                # cumulative_benchmark_returns[0] = 1 + aligned_benchmark_returns[0].
                # So, benchmark_equity_display[0] = initial_equity * (1 + aligned_benchmark_returns[0]).
                # This is correct if the first return is for the first day.
                # If the equity curve starts at T0, and first return is for T0->T1, then this is fine.
                
                # Check if the first day of benchmark_equity_display needs to be forced to initial_equity
                # This happens if the benchmark return for the very first day is non-zero.
                # For visual comparison, often the benchmark is normalized to start at the same point.
                if benchmark_equity_display.index[0] == first_equity_date:
                     # Adjust the first point to ensure it starts at the same visual level
                     # This is a common normalization for visual comparison.
                     # The relative performance (shape) is preserved.
                     if aligned_benchmark_returns.iloc[0] != 0.0 : # if first day return is not 0
                         # Re-calculate with first day's return effectively being 0 for the base
                         temp_returns = aligned_benchmark_returns.copy()
                         # temp_returns.iloc[0] = 0 # This would make the first day's plotted value initial_equity
                         # Then recalculate: initial_equity * (1 + temp_returns).cumprod()
                         # This is one way to normalize.
                         # Another way:
                         benchmark_equity_display = (benchmark_equity_display / benchmark_equity_display.iloc[0]) * initial_equity


                ax.plot(benchmark_equity_display.index, benchmark_equity_display, label="Benchmark Equity", linestyle='--')
                logger.info("PerformanceReporter: Plotted benchmark equity curve.")

        ax.set_title(self.config.get('plot_equity_title', "Equity Curve"))
        ax.set_xlabel("Date")
        ax.set_ylabel("Portfolio Value")
        ax.legend()
        ax.grid(True)

        if output_path:
            logger.info(f"PerformanceReporter: Attempting to save equity curve plot to {output_path}")
            plt.savefig(output_path)
            logger.info(f"PerformanceReporter: Equity curve plot saved to {output_path}")
        
        if show:
            logger.info("PerformanceReporter: Attempting to show equity curve plot.")
            plt.show()
        
        plt.close(fig) # Close the plot to free memory
        logger.info("PerformanceReporter: Equity curve plot figure closed.")

    def plot_drawdown_underwater(self, output_path: str = None, show: bool = True):
        logger.info(f"plot_drawdown_underwater called with output_path='{output_path}', show={show}")
        if self.daily_returns.empty:
            logger.warning("PerformanceReporter: Daily returns are empty. Cannot plot drawdown.")
            return

        qs_returns = self.daily_returns.copy()
        if not isinstance(qs_returns.index, pd.DatetimeIndex):
             qs_returns.index = pd.to_datetime(qs_returns.index)
        qs_returns.index = qs_returns.index.normalize()

        fig, ax = plt.subplots(figsize=self.config.get('plot_figsize', (12, 8)))
        try:
            quantstats.plots.drawdown(qs_returns, ax=ax, compounded=True, show=False) # show=False as we manage it
            ax.set_title(self.config.get('plot_drawdown_title', "Drawdown Underwater Plot"))

            if output_path:
                logger.info(f"PerformanceReporter: Attempting to save drawdown plot to {output_path}")
                fig.savefig(output_path)
                logger.info(f"PerformanceReporter: Drawdown plot saved to {output_path}")
            
            if show:
                logger.info("PerformanceReporter: Attempting to show drawdown plot.")
                plt.show()
            
        except Exception as e:
            logger.error(f"PerformanceReporter: Error plotting drawdown: {e}")
        finally:
            plt.close(fig) # Close the figure
            logger.info("PerformanceReporter: Drawdown plot figure closed.")

if __name__ == '__main__':
    # Example Usage
    # Configure logging for the example usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("PerformanceReporter class defined. Example run starting...")
    
    # Create dummy data for example
    np.random.seed(123) # For reproducibility of random numbers
    idx = pd.date_range(start='2023-01-01', end='2023-01-31', freq='D')
    
    initial_equity_value = 100000
    equity_values_list = [initial_equity_value]
    for i in range(1, len(idx)):
        change = np.random.normal(loc=50, scale=300) # Simulate daily P&L
        equity_values_list.append(equity_values_list[-1] + change)
    
    equity_curve_series = pd.Series(equity_values_list, index=idx, name="Equity")
    # Add some typical characteristics to equity curve
    equity_curve_series.iloc[10:15] -= 2000 # A sharper dip
    equity_curve_series.iloc[20:25] += 1500 # A recovery phase

    trades_data = {
        'entry_timestamp': pd.to_datetime(['2023-01-02', '2023-01-05', '2023-01-10', '2023-01-15', '2023-01-20']),
        'exit_timestamp': pd.to_datetime(['2023-01-04', '2023-01-08', '2023-01-12', '2023-01-18', '2023-01-22']),
        'symbol': ['AAPL', 'GOOG', 'AAPL', 'MSFT', 'GOOG'],
        'pnl': [300, -150, 500, -80, 400] # More realistic PnLs
    }
    trades_df = pd.DataFrame(trades_data)

    # Dummy benchmark (daily % returns)
    benchmark_daily_rets = pd.Series(np.random.normal(0.0003, 0.008, len(idx)), index=idx, name="Benchmark")
    # Ensure benchmark doesn't have extreme values for realistic plotting
    benchmark_daily_rets = benchmark_daily_rets.clip(-0.05, 0.05) 


    reporter_config = {
        'plot_figsize': (10,6),
        'plot_equity_title': "My Strategy Equity Journey",
        'plot_drawdown_title': "My Strategy Drawdown Profile"
    }

    reporter = PerformanceReporter(
        trades=trades_df, 
        equity_curve=equity_curve_series, 
        benchmark_returns=benchmark_daily_rets,
        config=reporter_config
    )
    
    logger.info("\n--- Daily Returns (Head) ---")
    logger.info(reporter.daily_returns.head())
 
    logger.info("\n--- Key Metrics ---")
    metrics = reporter.calculate_key_metrics()
    for k, v in metrics.items():
         logger.info(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
 
    logger.info("\n--- Generating QuantStats Report ---")
    reporter.generate_quantstats_report(output_path="strategy_performance_report.html", title="My Custom Strategy Analysis")
 
    logger.info("\n--- Plotting Equity Curve ---")
    reporter.plot_equity_curve(output_path="equity_curve.png", show=False)
 
    logger.info("\n--- Plotting Drawdown Underwater ---")
    reporter.plot_drawdown_underwater(output_path="drawdown_plot.png", show=False)
 
    logger.info("\nExample run finished. Check for 'strategy_performance_report.html', 'equity_curve.png', and 'drawdown_plot.png'.")
 
     # Test with equity curve not having DatetimeIndex initially
    logger.info("\n--- Test with non-DatetimeIndex equity curve ---")
    equity_values_non_dt_idx = equity_curve_series.copy()
    equity_values_non_dt_idx.index = range(len(equity_values_non_dt_idx)) # Non-datetime index
     
    reporter_non_dt_idx = PerformanceReporter(trades=trades_df, equity_curve=equity_values_non_dt_idx, benchmark_returns=benchmark_daily_rets)
    logger.info("Daily returns with auto-converted index:")
    logger.info(reporter_non_dt_idx.daily_returns.head()) # Should be empty or log error if conversion failed and not handled
    metrics_non_dt = reporter_non_dt_idx.calculate_key_metrics()
    logger.info("Metrics for non-DatetimeIndex test:")
    for k,v in metrics_non_dt.items():
        logger.info(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
     
     # Test with empty equity curve
    logger.info("\n--- Test with empty equity curve ---")
    reporter_empty_equity = PerformanceReporter(trades=trades_df, equity_curve=pd.Series(dtype=float, index=pd.to_datetime([])), benchmark_returns=benchmark_daily_rets)
    metrics_empty_equity = reporter_empty_equity.calculate_key_metrics()
    logger.info("Metrics for empty equity curve test:")
    for k,v in metrics_empty_equity.items():
        logger.info(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
    reporter_empty_equity.generate_quantstats_report() # Should print message and not fail
    reporter_empty_equity.plot_equity_curve(show=False) # Should print message
    reporter_empty_equity.plot_drawdown_underwater(show=False) # Should print message
 
    logger.info("\nFinished all example runs.")

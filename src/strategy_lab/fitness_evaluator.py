import uuid
import pandas as pd
import datetime
import inspect # For finding classes
from typing import Dict, Any, Optional, List, Type

from src.data_handler.historical_data_manager import HistoricalDataManager
from src.broker_api.mock_fyers_client import MockFyersClient
from src.backtester.engine import BacktesterEngine
# from src.backtester.metrics import calculate_all_metrics # Replaced by PerformanceReporter
from src.analytics.performance_reporter import PerformanceReporter # Added import
from src.core.models import Candle, Timeframe 
from src.strategies.base_strategy import BaseStrategy
import src # Import the src package to pass to exec

class FitnessEvaluator:
    """
    Evaluates the fitness of a trading strategy by running it through a backtester
    and calculating performance metrics using PerformanceReporter.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the FitnessEvaluator.

        Args:
            config (Optional[Dict[str, Any]]): Configuration for the evaluator (e.g., backtester settings).
        """
        self.config = config or {}
        # Updated default_error_metrics to align with PerformanceReporter keys
        # Values represent "bad" outcomes for these metrics.
        self.default_error_metrics = {
            "Total Return [%]": -float('inf'),
            "CAGR [%]": -float('inf'),
            "Sharpe Ratio": -float('inf'),
            "Sortino Ratio": -float('inf'),
            "Max Drawdown [%]": float('inf'), # Max drawdown is typically negative, so a large positive is "bad" if it's reported as positive %
            "Calmar Ratio": -float('inf'),
            "Total Trades": 0,
            "Win Rate [%]": 0.0,
            "Profit Factor": 0.0,
            "Avg Winning Trade PnL": 0.0,
            "Avg Losing Trade PnL": 0.0, # Should be 0 or negative; 0 implies no losing trades or no trades
            "error": "Evaluation did not complete successfully." # Default error message
        }
        # Ensure Max Drawdown from PerformanceReporter is handled consistently (it's positive percentage)
        # If PerformanceReporter returns MDD as negative, then -float('inf') would be the "bad" default.
        # PerformanceReporter's calculate_key_metrics returns Max Drawdown as a positive percentage.
        # So, a large positive value is indeed "bad" if we are minimizing drawdown.
        # However, for fitness, usually higher is better for returns/ratios, lower for drawdown.
        # Let's keep it as float('inf') for "worst possible" if it means higher is worse.
        # Or, if the fitness function will negate it, then -float('inf') is fine.
        # For now, assuming this dict is just for "what happened if error", not direct fitness input.
        # Let's stick to PerformanceReporter's typical output: Max Drawdown as positive percentage.
        # So, default_error_metrics["Max Drawdown [%]"] = float('inf') is a "worst case" placeholder.

    def _find_strategy_class(self, strategy_namespace: Dict[str, Any]) -> Optional[Type[BaseStrategy]]:
        """
        Finds the strategy class within the executed namespace.
        It looks for 'EvolvedStrategy' first, then any subclass of BaseStrategy.
        """
        if "EvolvedStrategy" in strategy_namespace and \
           isinstance(strategy_namespace["EvolvedStrategy"], type) and \
           issubclass(strategy_namespace["EvolvedStrategy"], BaseStrategy):
            return strategy_namespace["EvolvedStrategy"]

        for name, obj in strategy_namespace.items():
            if inspect.isclass(obj) and issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                return obj
        return None

    def _convert_trades_to_dataframe(self, trade_objects: list) -> pd.DataFrame:
        if not trade_objects:
            return pd.DataFrame()

        df = pd.DataFrame(trade_objects)
        
        # Ensure essential columns are present, others can be optional
        # 'pnl' is critical for PerformanceReporter trade metrics
        required_cols = {'symbol', 'side', 'quantity', 'price', 'timestamp', 'pnl'}
        for col in required_cols:
            if col not in df.columns:
                # Add missing column with NaNs or default values
                if col == 'pnl': df[col] = 0.0 
                elif col == 'timestamp': df[col] = pd.NaT
                elif col in ['quantity', 'price']: df[col] = 0.0
                else: df[col] = None 
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        numeric_cols = ['quantity', 'price', 'pnl', 'commission']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            elif col == 'pnl': # Ensure PnL exists even if not in original list and not caught by required_cols check earlier
                df[col] = 0.0


        return df

    def evaluate_strategy(self, strategy_code_string: str, historical_data_path: str, strategy_config: dict) -> dict:
        """
        Evaluates a single strategy using PerformanceReporter.
        """
        error_metrics_with_details = self.default_error_metrics.copy()
        strategy_namespace = {}
        strategy_class = None
        
        exec_globals = {
            'BaseStrategy': BaseStrategy, 'src': src, '__builtins__': __builtins__
        }
        try:
            exec(strategy_code_string, exec_globals, strategy_namespace)
            strategy_class = self._find_strategy_class(strategy_namespace) 
            if strategy_class is None:
                error_metrics_with_details["error"] = "No 'EvolvedStrategy' or BaseStrategy subclass found in strategy code."
                return error_metrics_with_details
        except Exception as e:
            error_metrics_with_details["error"] = f"Error executing strategy code: {str(e)}"
            return error_metrics_with_details

        candles_list: List[Candle] = []
        symbol = strategy_config.get("symbol", "UNKNOWN_SYMBOL") 
        try:
            df = pd.read_csv(historical_data_path)
            if df.empty:
                error_metrics_with_details["error"] = "Historical data CSV is empty."
                return error_metrics_with_details
            required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
            if not required_cols.issubset(df.columns):
                error_metrics_with_details["error"] = f"Historical data CSV missing required columns: {required_cols - set(df.columns)}"
                return error_metrics_with_details
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            for _, row in df.iterrows():
                candles_list.append(Candle(
                    timestamp=row['timestamp'], open=row['open'], high=row['high'],
                    low=row['low'], close=row['close'], volume=row['volume'], symbol=symbol
                ))
            if not candles_list:
                error_metrics_with_details["error"] = "No candles processed from historical data."
                return error_metrics_with_details
            start_date = candles_list[0].timestamp
            end_date = candles_list[-1].timestamp
        except Exception as e:
            error_metrics_with_details["error"] = f"Error loading or processing historical data: {str(e)}"
            return error_metrics_with_details
            
        try:
            initial_cash = self.config.get("initial_cash", 100000)
            commission_rate = self.config.get("commission_rate", 0.0007)
            data_feeds_for_broker = {symbol: candles_list}
            broker = MockFyersClient(
                historical_data=data_feeds_for_broker, initial_cash=initial_cash, commission_rate=commission_rate
            )
            hdm = HistoricalDataManager(broker_client=broker)
            strategy_id = f"evolved_strat_{uuid.uuid4()}"
            if "symbol" not in strategy_config: strategy_config["symbol"] = symbol
            strategy_instance = strategy_class(strategy_id=strategy_id, broker=broker, config=strategy_config)
            timeframe_value = strategy_config.get("timeframe", Timeframe.DAY_1.value)
            
            engine = BacktesterEngine(
                strategy=strategy_instance, broker=broker, historical_data_manager=hdm,
                symbols=[symbol], timeframe=timeframe_value, # Corrected: symbols_to_trade -> symbols
                start_date=start_date, end_date=end_date,
                generate_analytics_report=False # No need for engine to generate its own report here
            )
        except Exception as e:
            error_metrics_with_details["error"] = f"Error setting up backtester: {str(e)}"
            return error_metrics_with_details

        try:
            _, portfolio_history = engine.run() # engine.run() returns (equity_curve_raw_values, portfolio_history)
            trade_log = broker.get_trade_history()
            trade_df = self._convert_trades_to_dataframe(trade_log)

            if not portfolio_history:
                error_metrics_with_details["error"] = "Portfolio history is empty. Cannot generate analytics metrics."
                return error_metrics_with_details

            timestamps = [entry['timestamp'] for entry in portfolio_history]
            values = [entry['total_value'] for entry in portfolio_history]

            temp_df = pd.DataFrame({'timestamp': pd.to_datetime(timestamps), 'value': values})
            
            if temp_df.empty or temp_df['value'].isnull().all(): # Check if temp_df is empty or all values are null
                error_metrics_with_details["error"] = "Equity curve is empty or contains no valid values after processing portfolio_history."
                return error_metrics_with_details

            # Ensure timestamps are unique and sorted for Series creation
            # Group by timestamp and take the last entry for that timestamp to handle duplicates
            if temp_df['timestamp'].duplicated().any():
                temp_df = temp_df.groupby('timestamp').last()
            else:
                # If no duplicates, still set index for consistency before creating Series
                temp_df = temp_df.set_index('timestamp')

            equity_curve_series = pd.Series(temp_df['value'], name="Equity").sort_index()

            if equity_curve_series.empty: # Final check
                error_metrics_with_details["error"] = "Equity curve is empty after final processing. Cannot generate analytics metrics."
                return error_metrics_with_details
            
            reporter = PerformanceReporter(trades=trade_df, equity_curve=equity_curve_series, benchmark_returns=None)
            all_metrics = reporter.calculate_key_metrics()
            
            # Ensure all default metric keys are present in the final output, even if calculation failed partially
            # PerformanceReporter.calculate_key_metrics should ideally return all keys with default/error values
            # If not, we merge to ensure structure.
            final_metrics = self.default_error_metrics.copy()
            final_metrics.pop("error", None) # Remove default error message if we got metrics
            final_metrics.update(all_metrics) # Overlay calculated metrics
            
            return final_metrics
            
        except Exception as e:
            error_metrics_with_details["error"] = f"Error during backtest execution or metrics calculation: {str(e)}"
            # Log the full traceback for debugging if a logger was available
            # import traceback
            # self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return error_metrics_with_details

# Example Usage (for illustration, will not run in production directly)
if __name__ == '__main__':
    dummy_data = {
        'timestamp': pd.to_datetime(['2023-01-01 09:15:00', '2023-01-01 09:16:00', '2023-01-02 09:15:00', '2023-01-02 09:16:00', '2023-01-03 09:15:00']),
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [101, 102, 103, 104, 105],
        'volume': [1000, 1100, 1200, 1300, 1400]
    }
    dummy_df = pd.DataFrame(dummy_data)
    dummy_csv_path = "dummy_historical_data_fitness.csv" # Unique name
    dummy_df.to_csv(dummy_csv_path, index=False)

    sample_strategy_code = """
from src.strategies.base_strategy import BaseStrategy
from src.core.models import Order, OrderType, OrderSide

class EvolvedStrategy(BaseStrategy):
    def __init__(self, strategy_id, broker, config):
        super().__init__(strategy_id, broker, config)
        self.symbol = self.config.get("symbol", "MOCK_SYMBOL")
        self.bought = False
        # Access logger via self.logger if BaseStrategy provides it
        # For example: self.logger.info("EvolvedStrategy initialized")

    def on_bar(self, current_bars): # Renamed from on_bar to match BaseStrategy
        current_bar = current_bars.get(self.symbol)
        if not current_bar:
            return

        # Simple logic: buy on first bar, do nothing else to ensure some PNL.
        if not self.bought and self.broker.get_current_bar_index() == 0 : # Buy on first bar (index 0)
            # self.logger.info(f"EvolvedStrategy: Attempting to BUY {self.symbol} at {current_bar.close}")
            print(f"EvolvedStrategy: Attempting to BUY {self.symbol} at {current_bar.close}")
            order = Order(symbol=self.symbol, quantity=1, side=OrderSide.BUY, order_type=OrderType.MARKET)
            try:
                self.broker.place_order(order)
                self.bought = True
                # self.logger.info(f"EvolvedStrategy: BUY order placed for {self.symbol}")
                print(f"EvolvedStrategy: BUY order placed for {self.symbol}")
            except Exception as e:
                # self.logger.error(f"EvolvedStrategy: Error placing BUY order: {e}")
                print(f"EvolvedStrategy: Error placing BUY order: {e}")
    """
    # Note: The above strategy is extremely simple and will result in an open position.
    # PnL calculations in MockFyersClient and trade history generation are crucial for meaningful metrics.

    evaluator_config = {"initial_cash": 100000, "commission_rate": 0.001}
    evaluator = FitnessEvaluator(config=evaluator_config)
    
    strategy_parameters = { "symbol": "TEST_SYM" }

    print(f"Evaluating strategy with symbol: {strategy_parameters['symbol']}")
    results = evaluator.evaluate_strategy(
        strategy_code_string=sample_strategy_code,
        historical_data_path=dummy_csv_path,
        strategy_config=strategy_parameters
    )

    print("\n--- Fitness Evaluation Results (FitnessEvaluator) ---")
    # Check if 'error' key is present
    if results.get("error", "Evaluation did not complete successfully.") != "Evaluation did not complete successfully." and "error" in results :
         print(f"Error: {results['error']}")
    # Print all metrics if no critical error, or if error is just a field among others
    for metric, value in results.items():
        if metric == "error" and value == "Evaluation did not complete successfully." and len(results) > 1:
            continue # Skip printing default error if other metrics are present
        print(f"{metric}: {value}")
    
    import os
    try:
        os.remove(dummy_csv_path)
        print(f"Cleaned up {dummy_csv_path}")
    except OSError as e:
        print(f"Error removing {dummy_csv_path}: {e}")

    print("\n--- Test with faulty code (FitnessEvaluator) ---")
    faulty_code = "class MyInvalidStrategy(): def __init__(self): pass"
    # Recreate dummy file for this test
    if not os.path.exists(dummy_csv_path): dummy_df.to_csv(dummy_csv_path, index=False)
    results_faulty = evaluator.evaluate_strategy(
        faulty_code, dummy_csv_path, strategy_config={"symbol": "FAULT_SYM"}
    )
    print(results_faulty)
    if os.path.exists(dummy_csv_path): os.remove(dummy_csv_path)


    print("\n--- Test with non-existent data path (FitnessEvaluator) ---")
    results_no_data = evaluator.evaluate_strategy(
        sample_strategy_code, "non_existent_data.csv", strategy_config={"symbol": "NO_DATA_SYM"}
    )
    print(results_no_data)

[end of src/strategy_lab/fitness_evaluator.py]

import uuid
import pandas as pd
import datetime
import inspect # For finding classes
from typing import Dict, Any, Optional, List, Type

from algo_trading_framework.src.data_handler.historical_data_manager import HistoricalDataManager
from algo_trading_framework.src.broker_api.mock_fyers_client import MockFyersClient
from algo_trading_framework.src.backtester.engine import BacktesterEngine
from algo_trading_framework.src.backtester.metrics import calculate_all_metrics
from algo_trading_framework.src.core.models import Candle
from algo_trading_framework.src.core.enums import Timeframe
from src.strategies.base_strategy import BaseStrategy
import src # Import the src package to pass to exec

class FitnessEvaluator:
    """
    Evaluates the fitness of a trading strategy by running it through a backtester
    and calculating performance metrics.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the FitnessEvaluator.

        Args:
            config (Optional[Dict[str, Any]]): Configuration for the evaluator (e.g., backtester settings).
                                                Currently not used extensively.
        """
        self.config = config or {}
        self.default_error_metrics = {
            "total_return_pct": -float('inf'),
            "sharpe_ratio": -float('inf'),
            "sortino_ratio": -float('inf'),
            "max_drawdown_pct": -float('inf'),
            "win_rate_pct": -float('inf'),
            "profit_factor": -float('inf'),
            "total_trades": 0,
            "average_profit_per_trade": -float('inf'),
            "average_loss_per_trade": float('inf'),
            "error": "Evaluation did not complete successfully." # Default error message
        }

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

    def evaluate_strategy(self, strategy_code_string: str, historical_data_path: str, strategy_config: dict) -> dict:
        """
        Evaluates a single strategy.

        Args:
            strategy_code_string (str): The Python code string of the strategy.
            historical_data_path (str): Path to the CSV file containing historical market data.
                                         Expected columns: timestamp, open, high, low, close, volume.
            strategy_config (dict): Configuration specific to the strategy (e.g., symbol, parameters).

        Returns:
            dict: A dictionary containing performance metrics or an error message.
        """
        error_metrics_with_details = self.default_error_metrics.copy()
        strategy_namespace = {}
        strategy_class = None
        
        # 1. Dynamic Strategy Loading
        # Create a scope for exec, and pass BaseStrategy and src for imports within the template.
        exec_globals = {
            'BaseStrategy': BaseStrategy,
            'src': src,  # Make the 'src' package available for imports like 'from src.core...'
            '__builtins__': __builtins__
        }
        strategy_namespace = {} # Local scope for the executed code

        try:
            exec(strategy_code_string, exec_globals, strategy_namespace)
            strategy_class = self._find_strategy_class(strategy_namespace) 
            if strategy_class is None:
                error_metrics_with_details["error"] = "No 'EvolvedStrategy' or BaseStrategy subclass found in strategy code."
                return error_metrics_with_details
        except Exception as e:
            error_metrics_with_details["error"] = f"Error executing strategy code: {str(e)}"
            return error_metrics_with_details

        # 2. Data Loading and Preparation
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
            if not candles_list: # Should be caught by df.empty, but as a safeguard
                error_metrics_with_details["error"] = "No candles processed from historical data."
                return error_metrics_with_details
            start_date = candles_list[0].timestamp
            end_date = candles_list[-1].timestamp
        except FileNotFoundError:
            error_metrics_with_details["error"] = f"Historical data file not found: {historical_data_path}"
            return error_metrics_with_details
        except pd.errors.EmptyDataError: # For CSVs that exist but are totally empty or just headers
             error_metrics_with_details["error"] = f"Historical data file is empty or malformed (pandas EmptyDataError): {historical_data_path}"
             return error_metrics_with_details
        except Exception as e:
            error_metrics_with_details["error"] = f"Error loading or processing historical data: {str(e)}"
            return error_metrics_with_details
            
        # 3. Backtesting Setup
        try:
            initial_cash = self.config.get("initial_cash", 100000)
            commission_rate = self.config.get("commission_rate", 0.0007)
            
            # MockFyersClient should be initialized with the actual candle data for the symbol.
            data_feeds_for_broker = {symbol: candles_list}
            broker = MockFyersClient(
                historical_data=data_feeds_for_broker, # Pass loaded candles
                initial_cash=initial_cash,
                commission_rate=commission_rate,
                symbols_allowed=[symbol]
            )
            
            # HistoricalDataManager is initialized with the broker.
            # It will use broker.get_historical_data to fetch (which for MockFyersClient means using the data_feeds_for_broker).
            hdm = HistoricalDataManager(broker_client=broker)
            
            strategy_id = f"evolved_strat_{uuid.uuid4()}"
            if "symbol" not in strategy_config: strategy_config["symbol"] = symbol

            strategy_instance = strategy_class(strategy_id=strategy_id, broker=broker, config=strategy_config)
            
            timeframe_value = strategy_config.get("timeframe", Timeframe.DAY_1.value)
            
            engine = BacktesterEngine(
                strategy=strategy_instance, broker=broker, historical_data_manager=hdm,
                symbols_to_trade=[symbol], timeframe=timeframe_value,
                start_date=start_date, end_date=end_date
            )
        except Exception as e:
            error_metrics_with_details["error"] = f"Error setting up backtester: {str(e)}"
            return error_metrics_with_details

        # 4. Run Backtest and Calculate Metrics
        try:
            equity_curve, portfolio_history = engine.run()
            trade_log = broker.get_trade_history()

            if equity_curve.empty:
                 error_metrics_with_details["error"] = "Backtest engine returned an empty equity curve. No trades or activity."
                 # Keep default bad metrics, but add this specific error.
                 return error_metrics_with_details
            
            # Calculate backtest duration in days
            backtest_duration_days = (end_date - start_date).days
            if backtest_duration_days <= 0: # Avoid division by zero or negative duration
                backtest_duration_days = 1 

            # Calculate metrics
            # Assuming calculate_all_metrics can handle empty trade_log (e.g., if no trades occurred)
            metrics = calculate_all_metrics(
                equity_curve=equity_curve,
                trade_log=trade_log, # List of Order objects
                risk_free_rate_annual=self.config.get("risk_free_rate_annual", 0.02),
                backtest_duration_days=backtest_duration_days,
                trading_days_per_year=self.config.get("trading_days_per_year", 252)
            )
            return metrics # Successfully calculated metrics
            
        except Exception as e:
            error_metrics_with_details["error"] = f"Error during backtest execution or metrics calculation: {str(e)}"
            return error_metrics_with_details

# Example Usage (for illustration, will not run in production directly)
if __name__ == '__main__':
    # This block is for testing the FitnessEvaluator if run directly.
    # It requires setting up mock data and a sample strategy string.
    
    # Create a dummy CSV file for testing
    dummy_data = {
        'timestamp': pd.to_datetime(['2023-01-01 09:15:00', '2023-01-01 09:16:00', '2023-01-02 09:15:00', '2023-01-02 09:16:00', '2023-01-03 09:15:00']),
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [101, 102, 103, 104, 105],
        'volume': [1000, 1100, 1200, 1300, 1400]
    }
    dummy_df = pd.DataFrame(dummy_data)
    dummy_csv_path = "dummy_historical_data.csv"
    dummy_df.to_csv(dummy_csv_path, index=False)

    # Sample strategy code string (very basic)
    # Note: This strategy is very basic and might not generate trades.
    # A proper EvolvedStrategy would have more logic.
    sample_strategy_code = """
from algo_trading_framework.src.strategies.base_strategy import BaseStrategy
from algo_trading_framework.src.core.models import Order, OrderType, OrderSide

class EvolvedStrategy(BaseStrategy):
    def __init__(self, strategy_id, broker, config):
        super().__init__(strategy_id, broker, config)
        self.symbol = self.config.get("symbol", "MOCK_SYMBOL")
        self.bought = False

    def on_bar(self, current_bars):
        current_bar = current_bars.get(self.symbol)
        if not current_bar:
            return

        # Simple logic: buy on first bar, sell on third bar if bought
        if not self.bought:
            self.logger.info(f"EvolvedStrategy: Attempting to BUY {self.symbol} at {current_bar.close}")
            order = Order(symbol=self.symbol, quantity=1, side=OrderSide.BUY, order_type=OrderType.MARKET)
            try:
                self.broker.place_order(order)
                self.bought = True
                self.logger.info(f"EvolvedStrategy: BUY order placed for {self.symbol}")
            except Exception as e:
                self.logger.error(f"EvolvedStrategy: Error placing BUY order: {e}")
        elif self.broker.get_current_bar_index() >= 2 and self.bought: # Sell on 3rd bar (index 2)
            # Check if we have a position
            all_positions = self.broker.get_positions()
            active_position_qty = 0
            for pos in all_positions:
                if pos['symbol'] == self.symbol:
                    active_position_qty = pos.get('quantity',0)
                    break
            
            if active_position_qty > 0:
                self.logger.info(f"EvolvedStrategy: Attempting to SELL {self.symbol} at {current_bar.close}")
                order = Order(symbol=self.symbol, quantity=abs(active_position_qty), side=OrderSide.SELL, order_type=OrderType.MARKET)
                try:
                    self.broker.place_order(order)
                    self.bought = False # Allow re-buying if logic extended
                    self.logger.info(f"EvolvedStrategy: SELL order placed for {self.symbol}")
                except Exception as e:
                    self.logger.error(f"EvolvedStrategy: Error placing SELL order: {e}")
    """

    evaluator_config = {"initial_cash": 100000, "commission_rate": 0.001, "risk_free_rate_annual": 0.03}
    evaluator = FitnessEvaluator(config=evaluator_config)
    
    strategy_parameters = {
        "symbol": "TEST_SYM", 
        "some_param": 10 # Example param for the strategy
    }

    print(f"Evaluating strategy with symbol: {strategy_parameters['symbol']}")
    results = evaluator.evaluate_strategy(
        strategy_code_string=sample_strategy_code,
        historical_data_path=dummy_csv_path,
        strategy_config=strategy_parameters
    )

    print("\\n--- Fitness Evaluation Results ---")
    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        for metric, value in results.items():
            print(f"{metric}: {value}")
    
    # Clean up dummy CSV
    import os
    try:
        os.remove(dummy_csv_path)
        print(f"Cleaned up {dummy_csv_path}")
    except OSError as e:
        print(f"Error removing {dummy_csv_path}: {e}")

    print("\\n--- Test with faulty code ---")
    faulty_code = "class MyInvalidStrategy(): def __init__(self): pass" # Not inheriting BaseStrategy
    results_faulty = evaluator.evaluate_strategy(
        faulty_code, 
        dummy_csv_path, # Need to recreate for this test or handle absence
        strategy_config={"symbol": "FAULT_SYM"}
    )
    print(results_faulty)
    
    # Recreate dummy for next test if needed, or ensure tests are independent
    if not os.path.exists(dummy_csv_path):
        dummy_df.to_csv(dummy_csv_path, index=False)

    print("\\n--- Test with non-existent data path ---")
    results_no_data = evaluator.evaluate_strategy(
        sample_strategy_code, 
        "non_existent_data.csv", 
        strategy_config={"symbol": "NO_DATA_SYM"}
    )
    print(results_no_data)
    
    # Clean up dummy CSV if it was recreated
    if os.path.exists(dummy_csv_path):
        try:
            os.remove(dummy_csv_path)
            print(f"Cleaned up {dummy_csv_path} (final)")
        except OSError as e:
            print(f"Error removing {dummy_csv_path} (final): {e}")

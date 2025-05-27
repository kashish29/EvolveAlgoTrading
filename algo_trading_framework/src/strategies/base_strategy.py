from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd

# Assuming core.models and core.enums are accessible for Signal and TradeType
# Adjust import path if necessary based on actual project structure
try:
    from algo_trading_framework.src.core.models import Signal, Candle
    from algo_trading_framework.src.core.enums import TradeType, OrderType
except ImportError:
    print("Warning: Core models/enums not found at expected location during base_strategy.py load. Ensure PYTHONPATH.")
    # Define dummy classes if imports fail, for basic script integrity if run standalone (not recommended for framework use)
    class Signal: pass 
    class Candle: pass
    class TradeType: BUY="BUY"; SELL="SELL"
    class OrderType: MARKET="MARKET"


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Concrete strategies must implement the on_bar method.
    """
    def __init__(self, strategy_name: str, params: Dict[str, Any]):
        """
        Initializes the base strategy.

        Args:
            strategy_name (str): A descriptive name for the strategy.
            params (Dict[str, Any]): A dictionary of parameters for the strategy
                                     (e.g., {"short_window": 20, "long_window": 50}).
        """
        self.strategy_name = strategy_name
        self.params = params
        self.data_history = pd.DataFrame() # To store historical data for calculations
        print(f"Strategy '{self.strategy_name}' initialized with parameters: {self.params}")

    @abstractmethod
    def on_bar(self, current_candle: Candle, historical_data: Optional[pd.DataFrame] = None) -> Optional[Signal]:
        """
        Called on each new market data bar (candle).
        This is where the strategy logic to generate trading signals resides.

        Args:
            current_candle (Candle): The most recent candle data.
            historical_data (Optional[pd.DataFrame]): A DataFrame of historical candle data
                                                     available up to (but not including) the current_candle.
                                                     Useful for indicator calculations that require a lookback period.
                                                     The DataFrame should have columns like ['timestamp', 'open', 'high', 'low', 'close', 'volume'].

        Returns:
            Optional[Signal]: A Signal object if a trading signal is generated, otherwise None.
        """
        pass

    def update_historical_data(self, new_candle_data: Candle):
        """
        Updates the internal historical data store with the new candle.
        This is a helper that can be called by the backtesting engine or live trader
        before calling on_bar, if the strategy relies on on_bar's historical_data argument.
        Alternatively, strategies can manage their own history internally if preferred.
        
        Args:
            new_candle_data (Candle): The new candle to add.
        """
        candle_dict = {
            'timestamp': new_candle_data.timestamp,
            'open': new_candle_data.open,
            'high': new_candle_data.high,
            'low': new_candle_data.low,
            'close': new_candle_data.close,
            'volume': new_candle_data.volume,
            'symbol': new_candle_data.symbol,
            'timeframe': new_candle_data.timeframe
        }
        # Use pd.concat instead of append for efficiency
        new_row_df = pd.DataFrame([candle_dict])
        if self.data_history.empty:
            self.data_history = new_row_df
        else:
            self.data_history = pd.concat([self.data_history, new_row_df], ignore_index=True)
        
        # Optional: Limit history size to prevent memory issues
        # max_history_length = self.params.get("max_history_length", 1000) # Example parameter
        # if len(self.data_history) > max_history_length:
        #     self.data_history = self.data_history.iloc[-max_history_length:]

    def get_historical_data_for_on_bar(self) -> pd.DataFrame:
        """
        Returns the historical data collected so far, for use in on_bar.
        Excludes the very last row, as that would be the 'current_candle' data.
        """
        if len(self.data_history) > 1:
            return self.data_history.iloc[:-1].copy()
        return pd.DataFrame() # Return empty if not enough data

from datetime import datetime
import pandas as pd
from typing import Dict, Any, Optional, List

try:
    from .base_strategy import BaseStrategy
    from algo_trading_framework.src.core.models import Signal, Candle
    from algo_trading_framework.src.core.enums import TradeType, OrderType
except ImportError:
    print("Warning: BaseStrategy or core models/enums not found during example_strategy.py load.")
    # Dummy classes for standalone execution (not for framework use)
    class BaseStrategy: 
        def __init__(self, strategy_name, params): self.strategy_name = strategy_name; self.params = params; self.data_history = pd.DataFrame()
        def on_bar(self, current_candle, historical_data): pass
        def update_historical_data(self, new_candle_data): pass
        def get_historical_data_for_on_bar(self): return pd.DataFrame()

    class Signal:
        def __init__(self, timestamp, symbol, trade_type, order_type=None, price=None, quantity=1.0, comment=None):
            self.timestamp = timestamp
            self.symbol = symbol
            self.trade_type = trade_type
            self.order_type = order_type or OrderType.MARKET
            self.price = price
            self.quantity = quantity
            self.comment = comment
    class Candle: pass
    class TradeType: BUY="BUY"; SELL="SELL"
    class OrderType: MARKET="MARKET"


class ExampleMovingAverageCrossStrategy(BaseStrategy):
    """
    A simple example strategy based on moving average crossovers.
    Generates a BUY signal when the short-term moving average crosses above the long-term moving average.
    Generates a SELL signal when the short-term moving average crosses below the long-term moving average.
    """
    def __init__(self, strategy_name: str = "MovingAverageCross", params: Optional[Dict[str, Any]] = None):
        default_params = {"short_window": 10, "long_window": 20, "symbol": "MOCK_SYMBOL"}
        if params:
            default_params.update(params)
        
        super().__init__(strategy_name, default_params)
        
        self.short_window = self.params["short_window"]
        self.long_window = self.params["long_window"]
        self.symbol = self.params["symbol"] # Symbol for which signals are generated

        if self.short_window >= self.long_window:
            raise ValueError("Short window must be less than long window for MA Crossover.")
            
        # Internal state to track MAs from previous bar to detect crossover
        self.prev_short_ma: Optional[float] = None
        self.prev_long_ma: Optional[float] = None
        print(f"ExampleMovingAverageCrossStrategy '{self.strategy_name}' initialized for symbol '{self.symbol}' "
              f"with Short MA: {self.short_window}, Long MA: {self.long_window}")


    def on_bar(self, current_candle: Candle, historical_data: Optional[pd.DataFrame] = None) -> Optional[Signal]:
        """
        Processes a new bar of data to check for MA crossover signals.

        Args:
            current_candle (Candle): The most recent candle data.
            historical_data (Optional[pd.DataFrame]): A DataFrame of historical candle data.
                                                     If None, the strategy will use its internally managed history.
                                                     The DataFrame should have a 'close' column.
        Returns:
            Optional[Signal]: A Signal object if a crossover occurs, otherwise None.
        """
        
        # Use the provided historical_data if available, otherwise use the strategy's internal one.
        # The historical_data argument should contain data *before* current_candle.
        # We append current_candle's close to this history to calculate current MAs.
        
        if historical_data is None:
            # This path might be taken if the backtester/live engine doesn't pass historical_data directly
            # and relies on the strategy managing its own via update_historical_data.
            # For this example, we'll assume historical_data is primarily managed externally for MA calculation.
            # If not, the strategy would need more robust internal history management.
            history_df = self.data_history # self.data_history should include the current candle if updated prior to on_bar call
        else:
            history_df = historical_data.copy()
            # Add current candle's close to a temporary series for MA calculation
            current_data_point = pd.Series({'timestamp': current_candle.timestamp, 'close': current_candle.close})
            # If history_df is pd.DataFrame, convert current_data_point to DataFrame before concat
            current_df_point = pd.DataFrame([current_data_point])

            # Ensure 'close' column exists in history_df
            if 'close' not in history_df.columns and not history_df.empty:
                 print("Warning: 'close' column not in historical_data for MA calculation.")
                 return None # Cannot calculate MAs

            if history_df.empty:
                history_df = current_df_point
            else:
                history_df = pd.concat([history_df, current_df_point], ignore_index=True)


        if 'close' not in history_df.columns or len(history_df['close']) < self.long_window:
            # Not enough data to calculate the long moving average
            # print(f"Not enough data for {self.strategy_name}: have {len(history_df['close'])}, need {self.long_window}")
            return None

        # Calculate short and long moving averages using the 'close' prices
        short_ma = history_df['close'].rolling(window=self.short_window).mean().iloc[-1]
        long_ma = history_df['close'].rolling(window=self.long_window).mean().iloc[-1]

        signal = None
        current_time = current_candle.timestamp

        if pd.isna(short_ma) or pd.isna(long_ma):
            # MAs might be NaN if there's not enough data yet after rolling
            return None

        # print(f"{current_time} - {self.symbol}: Short MA: {short_ma:.2f}, Long MA: {long_ma:.2f}, Prev Short: {self.prev_short_ma}, Prev Long: {self.prev_long_ma}")

        if self.prev_short_ma is not None and self.prev_long_ma is not None:
            # Check for crossover
            if self.prev_short_ma <= self.prev_long_ma and short_ma > long_ma:
                # Bullish crossover
                signal = Signal(
                    timestamp=current_time,
                    symbol=self.symbol, # Use the configured symbol
                    trade_type=TradeType.BUY,
                    order_type=OrderType.MARKET,
                    quantity=1.0, # Example quantity
                    comment=f"Bullish Crossover: Short MA ({short_ma:.2f}) crossed above Long MA ({long_ma:.2f})"
                )
                print(f"{current_time} - {self.strategy_name} - {self.symbol}: BUY Signal generated. {signal.comment}")
            elif self.prev_short_ma >= self.prev_long_ma and short_ma < long_ma:
                # Bearish crossover
                signal = Signal(
                    timestamp=current_time,
                    symbol=self.symbol, # Use the configured symbol
                    trade_type=TradeType.SELL,
                    order_type=OrderType.MARKET,
                    quantity=1.0, # Example quantity
                    comment=f"Bearish Crossover: Short MA ({short_ma:.2f}) crossed below Long MA ({long_ma:.2f})"
                )
                print(f"{current_time} - {self.strategy_name} - {self.symbol}: SELL Signal generated. {signal.comment}")

        # Update previous MAs for the next bar
        self.prev_short_ma = short_ma
        self.prev_long_ma = long_ma

        return signal

# Example Usage (can be removed or commented out)
if __name__ == '__main__':
    # Create some mock candle data
    sample_data = []
    base_price = 100
    for i in range(30): # Need enough data for long_window
        ts = datetime(2023, 1, 1, 9, i+1)
        price_offset = i * 0.1 if i < 15 else (30-i) * 0.1 - 1 # Create a dip then rise for crossover
        candle = Candle() # Assuming Candle is a simple dataclass or object
        candle.timestamp = ts
        candle.open=base_price + price_offset - 0.5
        candle.high=base_price + price_offset + 1
        candle.low=base_price + price_offset - 1
        candle.close=base_price + price_offset
        candle.volume=1000 + i*10
        candle.symbol="TESTSYM-EQ"
        sample_data.append(candle)

    # Convert to DataFrame for historical_data argument
    hist_df_list = []

    strategy_params = {"short_window": 5, "long_window": 10, "symbol": "TESTSYM-EQ"}
    strategy = ExampleMovingAverageCrossStrategy(params=strategy_params)

    print(f"\nRunning {strategy.strategy_name} with params: {strategy.params}")
    for i in range(len(sample_data)):
        current_c = sample_data[i]
        
        # Prepare historical data for on_bar: all data UP TO the current candle
        # The on_bar method itself will append the current candle's close for its calculation if needed
        historical_candles_for_on_bar = pd.DataFrame([{
            'timestamp':c.timestamp, 'open':c.open, 'high':c.high, 'low':c.low, 'close':c.close, 'volume':c.volume
        } for c in sample_data[:i]]) # Pass data *before* current_c


        # Call on_bar
        sig = strategy.on_bar(current_c, historical_data=historical_candles_for_on_bar)
        if sig:
            print(f"-> Signal at {sig.timestamp}: {sig.trade_type.value} {sig.symbol} due to {sig.comment}")

        # The strategy's internal update_historical_data might also be used by a backtester
        # strategy.update_historical_data(current_c) 
        # If using strategy's internal history, then on_bar might be called as:
        # sig = strategy.on_bar(current_c, historical_data=strategy.get_historical_data_for_on_bar())

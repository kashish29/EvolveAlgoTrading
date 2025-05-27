import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from algo_trading_framework.src.core.models import Signal, Order, Trade, Position, Candle
    from algo_trading_framework.src.core.enums import OrderType, OrderStatus, TradeType, InstrumentType
    from algo_trading_framework.src.strategies.base_strategy import BaseStrategy
    from .metrics import get_performance_summary # Assuming metrics.py is in the same directory
except ImportError:
    print("Warning: Core models, BaseStrategy or metrics not found during backtester/engine.py load.")
    # Dummy classes for standalone execution
    class Signal: pass
    class Order: pass
    class Trade: 
        def __init__(self, trade_id, order_id, timestamp, symbol, trade_type, quantity, price, commission, pnl=0): # Added pnl
            self.trade_id = trade_id
            self.order_id = order_id
            self.timestamp = timestamp
            self.symbol = symbol
            self.trade_type = trade_type
            self.quantity = quantity
            self.price = price
            self.commission = commission
            self.pnl = pnl # Initialize pnl

    class Position: 
        def __init__(self, symbol, instrument_type, quantity=0, average_entry_price=0.0, realized_pnl=0.0, last_updated=None):
            self.symbol = symbol
            self.instrument_type = instrument_type
            self.quantity = quantity
            self.average_entry_price = average_entry_price
            self.realized_pnl = realized_pnl
            self.last_updated = last_updated
            
    class Candle: pass
    class OrderType: MARKET="MARKET"; LIMIT="LIMIT"
    class OrderStatus: FILLED="FILLED"; OPEN="OPEN"; PENDING="PENDING"
    class TradeType: BUY="BUY"; SELL="SELL"
    class InstrumentType: EQUITY="EQUITY"
    class BaseStrategy:
        def __init__(self, name, params): self.strategy_name = name; self.params = params or {} # strategy_name added
        def on_bar(self, candle, history): pass
        def update_historical_data(self, candle): pass 
        def get_historical_data_for_on_bar(self): return pd.DataFrame() 

    def get_performance_summary(portfolio_history, trades, initial_capital): return {}


class BacktestEngine:
    def __init__(self, strategy_instance: BaseStrategy, historical_data: pd.DataFrame,
                 initial_capital: float = 100000.0, commission_per_trade: float = 0.01): 
        self.strategy = strategy_instance
        self.historical_data = historical_data.sort_values(by='timestamp').reset_index(drop=True)
        self.initial_capital = initial_capital
        self.commission_per_trade = commission_per_trade 

        self.cash = initial_capital
        self.portfolio_value = initial_capital
        self.positions: Dict[str, Position] = {} 
        self.trades: List[Trade] = []
        self.orders: List[Order] = [] # Although Order objects aren't fully used, list is here
        self.portfolio_history: List[Dict[str, Any]] = [] 

        self._validate_data()
        print(f"BacktestEngine initialized for strategy '{self.strategy.strategy_name}' "
              f"with initial capital: {self.initial_capital:.2f}")

    def _validate_data(self):
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'symbol'] 
        for col in required_cols:
            if col not in self.historical_data.columns:
                raise ValueError(f"Historical data is missing required column: {col}")
        if not pd.api.types.is_datetime64_any_dtype(self.historical_data['timestamp']):
            try:
                self.historical_data['timestamp'] = pd.to_datetime(self.historical_data['timestamp'])
            except Exception as e:
                raise ValueError(f"Timestamp column could not be converted to datetime: {e}")


    def _process_signal(self, signal: Signal, current_candle: Candle):
        print(f"Processing Signal at {current_candle.timestamp}: {signal.trade_type.value} {signal.quantity} {signal.symbol} @ {signal.order_type.value} (Price: {signal.price})")
        
        order_id_base = f"bt_ord_{len(self.trades)}_{int(current_candle.timestamp.timestamp())}" # Changed to use len(self.trades) for uniqueness

        fill_price = None
        status = OrderStatus.PENDING # Default status
        
        if signal.order_type == OrderType.MARKET:
            fill_price = current_candle.close
            status = OrderStatus.FILLED
        elif signal.order_type == OrderType.LIMIT:
            if signal.trade_type == TradeType.BUY:
                if current_candle.low <= signal.price: 
                    fill_price = min(current_candle.open, signal.price) 
                    status = OrderStatus.FILLED
            elif signal.trade_type == TradeType.SELL:
                if current_candle.high >= signal.price: 
                    fill_price = max(current_candle.open, signal.price) 
                    status = OrderStatus.FILLED
        else:
            print(f"Order type {signal.order_type} not yet fully supported in this basic backtester.")
            return

        if status == OrderStatus.FILLED and fill_price is not None:
            cost_or_proceeds = signal.quantity * fill_price
            commission_cost = signal.quantity * self.commission_per_trade

            if signal.trade_type == TradeType.BUY:
                if self.cash < cost_or_proceeds + commission_cost:
                    print(f"Insufficient cash to execute BUY for {signal.symbol}. Have {self.cash}, need {cost_or_proceeds + commission_cost}")
                    return 
                self.cash -= (cost_or_proceeds + commission_cost)
            else: 
                self.cash += (cost_or_proceeds - commission_cost)

            # The pnl for this specific trade will be calculated in _update_position
            trade = Trade(
                trade_id=f"bt_trd_{len(self.trades)}_{int(current_candle.timestamp.timestamp())}",
                order_id=order_id_base, 
                timestamp=current_candle.timestamp,
                symbol=signal.symbol,
                trade_type=signal.trade_type,
                quantity=signal.quantity,
                price=fill_price,
                commission=commission_cost,
                pnl=0 # Initialize PnL as 0; will be updated in _update_position
            )
            self.trades.append(trade)
            self._update_position(trade) # This will also set trade.pnl
            print(f"Trade Executed: {trade.trade_type.value} {trade.quantity} {trade.symbol} @ {trade.price:.2f}, "
                  f"Commission: {trade.commission:.2f}, PnL on this trade: {trade.pnl:.2f}, Cash: {self.cash:.2f}")
        else:
            print(f"Order for {signal.symbol} did not fill at {current_candle.timestamp}.")


    def _update_position(self, trade: Trade):
        symbol = trade.symbol
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                instrument_type=InstrumentType.EQUITY, 
                quantity=0,
                average_entry_price=0.0,
                realized_pnl=0.0 # Ensure initialized
            )
        
        position = self.positions[symbol]
        trade_pnl = 0 # PnL for this specific trade

        # Store current position state before modification for PnL calculation
        old_quantity = position.quantity
        old_avg_price = position.average_entry_price

        if old_quantity != 0: # If there's an existing position
            if (trade.trade_type == TradeType.SELL and old_quantity > 0) or \
               (trade.trade_type == TradeType.BUY and old_quantity < 0): # Closing or reducing a position
                
                qty_closed = min(abs(old_quantity), trade.quantity)
                
                if old_quantity > 0: # Closing/reducing long
                    trade_pnl = (trade.price - old_avg_price) * qty_closed 
                else: # Closing/reducing short
                    trade_pnl = (old_avg_price - trade.price) * qty_closed
                
                # Commission for this trade is already applied to cash. 
                # PnL should reflect profit before this specific trade's commission for clarity,
                # or after, consistently. Let's make PnL net of its own commission.
                trade_pnl -= trade.commission # Net PnL for this trade
                
                position.realized_pnl += trade_pnl
        
        trade.pnl = trade_pnl # Assign calculated PnL to the trade object

        # Update position quantity and average price
        if trade.trade_type == TradeType.BUY:
            new_total_quantity = position.quantity + trade.quantity
            if old_quantity < 0 and new_total_quantity > 0: # Flipped from short to long
                 position.average_entry_price = trade.price
            elif old_quantity < 0 and new_total_quantity <= 0: # Covering short, but not flipping
                 pass # Average entry price of remaining short position doesn't change
            elif old_quantity >= 0 : # Adding to long or opening long
                current_total_value = old_avg_price * old_quantity
                position.average_entry_price = (current_total_value + trade.quantity * trade.price) / new_total_quantity if new_total_quantity else 0
            position.quantity = new_total_quantity
        else: # SELL
            new_total_quantity = position.quantity - trade.quantity
            if old_quantity > 0 and new_total_quantity < 0: # Flipped from long to short
                position.average_entry_price = trade.price
            elif old_quantity > 0 and new_total_quantity >=0: # Reducing long, but not flipping
                pass # Average entry price of remaining long position doesn't change
            elif old_quantity <= 0: # Adding to short or opening short
                current_total_value = old_avg_price * old_quantity # old_avg_price here is avg price shares were shorted at
                # (abs(old_avg_price * old_quantity) + trade.quantity * trade.price) / abs(new_total_quantity)
                if new_total_quantity != 0 :
                    position.average_entry_price = (abs(current_total_value) + trade.quantity * trade.price) / abs(new_total_quantity)
                else: # Position fully closed
                    position.average_entry_price = 0
            position.quantity = new_total_quantity

        if position.quantity == 0: # If position is now flat
            position.average_entry_price = 0.0
            
        position.last_updated = trade.timestamp
        print(f"Position Updated: {symbol}, Qty: {position.quantity}, AvgPrice: {position.average_entry_price:.2f}, Cum.Realized PnL: {position.realized_pnl:.2f}")


    def _calculate_portfolio_value(self, current_timestamp: datetime):
        current_market_value = self.cash
        for symbol, position in self.positions.items():
            if position.quantity != 0:
                latest_price_series = self.historical_data[
                    (self.historical_data['symbol'] == symbol) &
                    (self.historical_data['timestamp'] == current_timestamp)
                ]['close']

                if not latest_price_series.empty:
                    latest_price = latest_price_series.iloc[0]
                    current_market_value += position.quantity * latest_price
                else: # If price not found for current timestamp (e.g. data ends for this symbol)
                      # Value at average entry price (conservative) or last known price (more complex)
                      # For simplicity, if no current price, assume its value contributes based on avg_entry_price
                      # This is not ideal for unrealized P&L but keeps value from vanishing if data is ragged
                    current_market_value += position.quantity * position.average_entry_price
        return current_market_value

    def run(self) -> Dict[str, Any]:
        print(f"Running backtest for strategy '{self.strategy.strategy_name}'...")
        
        for index, row in self.historical_data.iterrows():
            current_candle = Candle(
                timestamp=row['timestamp'], 
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume'), 
                symbol=row['symbol'],
            )
            
            history_for_strategy = pd.DataFrame() # Default to empty if index is 0
            if index > 0:
                 history_for_strategy = self.historical_data.iloc[:index].copy()


            signal = self.strategy.on_bar(current_candle, historical_data=history_for_strategy)

            if signal:
                self._process_signal(signal, current_candle)
            
            current_portfolio_value = self._calculate_portfolio_value(current_candle.timestamp)
            self.portfolio_history.append({
                "timestamp": current_candle.timestamp,
                "portfolio_value": current_portfolio_value,
                "cash": self.cash,
            })

        print("Backtest finished.")
        self._liquidate_open_positions() 

        portfolio_history_df = pd.DataFrame(self.portfolio_history)
        return get_performance_summary(portfolio_history_df, self.trades, self.initial_capital)

    def _liquidate_open_positions(self):
        print("Liquidating open positions at the end of backtest...")
        if self.historical_data.empty:
            print("No historical data to determine liquidation prices.")
            return
            
        last_timestamp = self.historical_data['timestamp'].iloc[-1]
        
        # Need a mutable list of items if dict changes during iteration (it does)
        for symbol in list(self.positions.keys()): 
            position = self.positions[symbol]
            if position.quantity != 0:
                last_price_series = self.historical_data[
                    (self.historical_data['symbol'] == symbol) &
                    (self.historical_data['timestamp'] == last_timestamp)
                ]['close']

                if not last_price_series.empty:
                    last_price = last_price_series.iloc[0]
                    print(f"Liquidating {position.quantity} of {symbol} at {last_price}")
                    
                    trade_type = TradeType.SELL if position.quantity > 0 else TradeType.BUY
                    qty_to_liquidate = abs(position.quantity)
                    
                    # Create a mock signal for liquidation processing via _process_signal
                    # Price for MARKET order signal is not strictly needed by _process_signal but good for clarity
                    liquidation_signal = Signal() # Using a dummy signal object for simplicity
                    setattr(liquidation_signal, 'timestamp', last_timestamp)
                    setattr(liquidation_signal, 'symbol', symbol)
                    setattr(liquidation_signal, 'trade_type', trade_type)
                    setattr(liquidation_signal, 'order_type', OrderType.MARKET)
                    setattr(liquidation_signal, 'quantity', qty_to_liquidate)
                    setattr(liquidation_signal, 'price', last_price) # For record / if logic changes

                    # Mock candle for processing liquidation (only close price is used by MARKET order fill)
                    mock_liquidation_candle = Candle()
                    setattr(mock_liquidation_candle, 'timestamp', last_timestamp)
                    setattr(mock_liquidation_candle, 'open', last_price)
                    setattr(mock_liquidation_candle, 'high', last_price)
                    setattr(mock_liquidation_candle, 'low', last_price)
                    setattr(mock_liquidation_candle, 'close', last_price)
                    setattr(mock_liquidation_candle, 'volume', 0)
                    setattr(mock_liquidation_candle, 'symbol', symbol)

                    self._process_signal(liquidation_signal, mock_liquidation_candle) 
                else:
                    print(f"Could not find last price for {symbol} to liquidate. Position value may be based on last avg price.")
        
        # Final portfolio value update after liquidation
        # After all liquidations, portfolio value should ideally be just cash.
        # However, _calculate_portfolio_value is based on last known prices for any *remaining* positions.
        # If all liquidated, self.cash is the final value.
        self.portfolio_value = self.cash 
        
        # Ensure there's at least one entry in portfolio_history before trying to access last timestamp
        last_hist_timestamp = self.historical_data['timestamp'].iloc[-1] if not self.historical_data.empty else datetime.now()

        self.portfolio_history.append({
            "timestamp": last_hist_timestamp,
            "portfolio_value": self.portfolio_value,
            "cash": self.cash,
        })
        print(f"All positions attempted liquidation. Final cash: {self.cash:.2f}")

```

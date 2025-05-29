import logging # Will use logger from BaseStrategy
from .base_strategy import BaseStrategy
from src.core.models import Order, OrderType, OrderSide, Candle # type: ignore
from typing import TYPE_CHECKING, Dict, List, Optional
import uuid

if TYPE_CHECKING: # pragma: no cover
    from src.broker_api.base_broker_client import BaseBrokerClient # type: ignore

class ExampleMovingAverageCrossStrategy(BaseStrategy):
    def __init__(self, strategy_id: str, broker: 'BaseBrokerClient', config: Optional[dict] = None):
        super().__init__(strategy_id, broker, config)
        
        self.symbol = self.config.get("symbol", "DEFAULT_SYMBOL") # e.g., "SBIN-EQ"
        self.short_window = self.config.get("short_window", 5)
        self.long_window = self.config.get("long_window", 10)
        self.quantity = self.config.get("quantity", 1)
        
        self.prices: List[float] = []
        self.short_ma_values: List[float] = []
        self.long_ma_values: List[float] = []
        
        self.logger.info(
            f"ExampleMovingAverageCrossStrategy '{self.strategy_id}' initialized for {self.symbol} "
            f"with short_window={self.short_window}, long_window={self.long_window}, quantity={self.quantity}."
        )

    def _calculate_sma(self, data: List[float], window: int) -> float | None:
        if len(data) < window:
            return None
        return sum(data[-window:]) / window

    def on_bar(self, current_bars: Dict[str, 'Candle']):
        current_bar = current_bars.get(self.symbol)
        
        if not current_bar:
            self.logger.debug(f"No current bar data for symbol {self.symbol} at this timestamp.")
            return

        self.prices.append(current_bar.close)
        if len(self.prices) > self.long_window + 5: # Keep a reasonable buffer, trim older prices
            self.prices.pop(0)

        short_ma = self._calculate_sma(self.prices, self.short_window)
        long_ma = self._calculate_sma(self.prices, self.long_window)

        if short_ma is not None: self.short_ma_values.append(short_ma)
        if long_ma is not None: self.long_ma_values.append(long_ma)

        self.logger.debug(f"Symbol: {self.symbol}, Close: {current_bar.close}, ShortMA: {short_ma}, LongMA: {long_ma}")

        if short_ma is None or long_ma is None:
            self.logger.debug("Not enough data for MA calculation yet.")
            return

        # --- Broker Interaction ---
        # MockFyersClient.get_positions() returns a list of position dictionaries
        all_positions = self.broker.get_positions() # list of dicts
        active_position = None
        for pos_dict in all_positions:
            if pos_dict.get('symbol') == self.symbol:
                active_position = pos_dict
                break
        
        # Buy Signal: Short MA crosses above Long MA
        # Ensure we use the previous MAs for crossover detection to avoid acting on the current bar's forming MA.
        if len(self.short_ma_values) < 2 or len(self.long_ma_values) < 2:
            # Need at least two values to detect a crossover from previous bar
            return

        prev_short_ma = self.short_ma_values[-2]
        prev_long_ma = self.long_ma_values[-2]
        current_short_ma = short_ma
        current_long_ma = long_ma

        # Buy Signal: short MA crosses above long MA
        if current_short_ma > current_long_ma and prev_short_ma <= prev_long_ma:
            current_pos_qty = active_position.get('quantity', 0) if active_position else 0
            if current_pos_qty == 0: # Only buy if not already holding a position
                order = Order(
                    id=str(uuid.uuid4()),
                    symbol=self.symbol,
                    quantity=self.quantity,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET
                )
                try:
                    order_id, status = self.broker.place_order(order)
                    self.logger.info(f"BUY signal for {self.symbol}. Placed MARKET order for {self.quantity} shares. Order ID: {order_id}, Status: {status}")
                except Exception as e:
                    self.logger.error(f"Error placing BUY order for {self.symbol}: {e}")
            else:
                self.logger.debug(f"BUY signal for {self.symbol}, but already have position qty: {current_pos_qty}. No action.")

        # Sell Signal: Short MA crosses below Long MA
        elif current_short_ma < current_long_ma and prev_short_ma >= prev_long_ma:
            current_pos_qty = active_position.get('quantity', 0) if active_position else 0
            if current_pos_qty > 0: # Only sell if holding a long position
                order = Order(
                    id=str(uuid.uuid4()),
                    symbol=self.symbol,
                    quantity=abs(current_pos_qty), # Sell the existing quantity
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET
                )
                try:
                    order_id, status = self.broker.place_order(order)
                    self.logger.info(f"SELL signal for {self.symbol}. Placed MARKET order for {abs(current_pos_qty)} shares. Order ID: {order_id}, Status: {status}")
                except Exception as e:
                    self.logger.error(f"Error placing SELL order for {self.symbol}: {e}")
            else:
                self.logger.debug(f"SELL signal for {self.symbol}, but no active long position (qty: {current_pos_qty}). No action.")

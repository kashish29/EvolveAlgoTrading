from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from .enums import OrderType, OrderStatus, TradeType, InstrumentType

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None # Or use Timeframe enum if preferred for storage

@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    trade_type: TradeType  # BUY or SELL
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None  # Required for LIMIT orders
    stop_price: Optional[float] = None # Required for STOP orders
    quantity: Optional[float] = 1.0 # Default quantity
    comment: Optional[str] = None

@dataclass
class Order:
    order_id: str = field(default_factory=lambda: f"ord_{int(datetime.now().timestamp() * 1e6)}")
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str
    trade_type: TradeType
    order_type: OrderType
    quantity: float
    status: OrderStatus = OrderStatus.PENDING
    price: Optional[float] = None          # Entry price for limit orders, fill price for market orders
    stop_price: Optional[float] = None
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    commission: float = 0.0
    instrument_type: Optional[InstrumentType] = InstrumentType.EQUITY
    parent_signal_id: Optional[str] = None # If generated from a Signal object

@dataclass
class Trade:
    trade_id: str = field(default_factory=lambda: f"trd_{int(datetime.now().timestamp() * 1e6)}")
    order_id: str
    timestamp: datetime
    symbol: str
    trade_type: TradeType
    quantity: float
    price: float # Execution price for this specific trade/fill
    commission: float = 0.0
    instrument_type: Optional[InstrumentType] = InstrumentType.EQUITY

@dataclass
class Position:
    symbol: str
    instrument_type: InstrumentType
    quantity: float = 0.0 # Can be positive (long) or negative (short)
    average_entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    last_updated: Optional[datetime] = None

    def update_position(self, trade: Trade):
        self.last_updated = trade.timestamp
        self.realized_pnl += self.quantity * (trade.price - self.average_entry_price) if self.quantity != 0 and trade.trade_type != self.current_trade_type() else 0

        if self.quantity == 0: # New position
            self.average_entry_price = trade.price
            self.quantity = trade.quantity if trade.trade_type == TradeType.BUY else -trade.quantity
        elif (trade.trade_type == TradeType.BUY and self.quantity > 0) or \
             (trade.trade_type == TradeType.SELL and self.quantity < 0): # Averaging into position
            current_value = self.average_entry_price * abs(self.quantity)
            trade_value = trade.price * trade.quantity
            total_quantity = abs(self.quantity) + trade.quantity
            self.average_entry_price = (current_value + trade_value) / total_quantity
            self.quantity += trade.quantity if trade.trade_type == TradeType.BUY else -trade.quantity
        else: # Closing some or all of position
            if abs(self.quantity) >= trade.quantity:
                self.quantity += -trade.quantity if trade.trade_type == TradeType.SELL else trade.quantity
                if self.quantity == 0:
                    self.average_entry_price = 0
            else: # Position reversed
                self.average_entry_price = trade.price
                self.quantity = trade.quantity - abs(self.quantity) if trade.trade_type == TradeType.BUY else -(trade.quantity - abs(self.quantity))
        # Unrealized P&L would typically be updated by a separate market data feed.

    def current_trade_type(self) -> Optional[TradeType]:
        if self.quantity > 0:
            return TradeType.BUY
        elif self.quantity < 0:
            return TradeType.SELL
        return None

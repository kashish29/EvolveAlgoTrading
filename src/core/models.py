from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional # Keep List if Signal or other parts need it.

from src.core.enums import Timeframe, OrderType, OrderStatus, OrderSide, InstrumentType

# --- Data Classes ---

@dataclass
class Candle: # Merged, using src copy structure primarily
    timestamp: datetime
    symbol: str # From src copy
    open: float
    high: float
    low: float
    close: float
    volume: int = 0 # From src copy (was Optional[int] before)
    timeframe: Optional[Timeframe] = None # From src copy (using Timeframe enum)

@dataclass
class Signal: # Retained from src, adapted enums
    timestamp: datetime
    symbol: str
    side: OrderSide  # Changed from trade_type: TradeType
    order_type: OrderType = OrderType.MARKET # Uses local OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    quantity: Optional[float] = 1.0
    comment: Optional[str] = None
    action: OrderSide = OrderSide.BUY

@dataclass
class Order: # From src copy, with minor adaptations
    id: str # from src copy (was order_id with default factory)
    symbol: str
    quantity: int # from src copy (was float)
    side: OrderSide # from src copy (was trade_type: TradeType)
    order_type: OrderType # Uses local OrderType
    price: Optional[float] = None      # Price for LIMIT order (was Optional[float])
    trigger_price: Optional[float] = None  # Trigger price for STOP or STOP_LIMIT order (from src copy)
    status: OrderStatus = OrderStatus.PENDING # Uses local OrderStatus
    timestamp: Optional[datetime] = None   # Timestamp of creation/acceptance by broker (was datetime default factory)
    executed_price: Optional[float] = None # Average price at which the order was filled (from src copy)
    filled_timestamp: Optional[datetime] = None # Timestamp of fill (from src copy)
    commission: Optional[float] = None # from src copy (was float)
    tag: Optional[str] = None          # Optional tag for strategy use (from src copy)
    parent_order_id: Optional[str] = None # For future use (from src copy)
    reject_reason: Optional[str] = None # Reason for rejection (from src copy)
    modified_timestamp: Optional[datetime] = None # Timestamp of last modification (from src copy)
    # Fields from original Order not directly in src copy:
    # filled_quantity: float = 0.0 -> Covered by updates to quantity or separate trade records
    # average_fill_price: Optional[float] = None -> Renamed to executed_price
    # instrument_type: Optional[InstrumentType] = InstrumentType.EQUITY -> Could be added if needed system-wide
    # parent_signal_id: Optional[str] = None -> Could be added if linking to Signal is important

@dataclass
class Trade: # From src copy, with minor adaptations
    trade_id: str # from src copy (was default factory)
    order_id: str
    symbol: str
    quantity: int # from src copy (was float)
    price: float  # Execution price for this trade
    side: OrderSide # from src copy (was trade_type: TradeType)
    timestamp: datetime # Execution timestamp for this trade
    commission: float = 0.0 # from src copy (was float)
    pnl: float = 0.0 # Added for realized PnL in backtesting
    tag: Optional[str] = None # Optional tag inherited from order (from src copy)
    # Fields from original Trade not directly in src copy:
    # instrument_type: Optional[InstrumentType] = InstrumentType.EQUITY -> Could be added

@dataclass
class Position: # From src copy
    symbol: str
    quantity: int                     # Positive for long, negative for short (was float)
    average_price: float              # (was average_entry_price)
    last_price: float = 0.0           # Last traded price for this position, used for PnL calc
    pnl: float = 0.0                  # Overall P&L (realized + unrealized)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    # instrument_type from original Position is not in src copy version. Could be added.
    # last_updated from original Position is not in src copy version.
    # update_position method and current_trade_type method from original are omitted,
    # as PnL calculation is expected to be handled differently with this model.

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class Timeframe(Enum):
    MINUTE_1 = "1minute"
    MINUTE_3 = "3minute"
    MINUTE_5 = "5minute"
    MINUTE_10 = "10minute"
    MINUTE_15 = "15minute"
    MINUTE_30 = "30minute"
    HOUR_1 = "1hour"
    DAY_1 = "1day"
    WEEK_1 = "1week"
    MONTH_1 = "1month"

@dataclass
class Candle:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    timeframe: Timeframe = None

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(Enum):
    PENDING = "PENDING"       # Order is pending submission or acknowledgement
    ACCEPTED = "ACCEPTED"     # Order is accepted by the broker, awaiting execution
    REJECTED = "REJECTED"     # Order is rejected by the broker
    COMPLETED = "COMPLETED"   # Order is fully executed
    CANCELLED = "CANCELLED"   # Order is cancelled
    MODIFIED = "MODIFIED"     # Order has been modified (could be an interim status or just a flag)
    TRIGGERED = "TRIGGERED"   # Stop order has been triggered and is now a market/limit order

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Order:
    id: str
    symbol: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    price: float = None               # Price for LIMIT order
    trigger_price: float = None       # Trigger price for STOP or STOP_LIMIT order
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = None        # Timestamp of creation/acceptance by broker
    executed_price: float = None      # Average price at which the order was filled
    filled_timestamp: datetime = None # Timestamp of fill
    commission: float = None
    tag: str = None                   # Optional tag for strategy use
    parent_order_id: str = None       # For future use, e.g. bracket orders
    reject_reason: str = None       # Reason for rejection, if any
    modified_timestamp: datetime = None # Timestamp of last modification

@dataclass
class Position:
    symbol: str
    quantity: int                     # Positive for long, negative for short
    average_price: float
    last_price: float = 0.0           # Last traded price for this position, used for PnL calc
    # P&L fields can be calculated dynamically, but storing them can be useful for snapshots
    pnl: float = 0.0                  # Overall P&L (realized + unrealized)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

@dataclass
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    quantity: int
    price: float                      # Execution price for this trade
    side: OrderSide
    timestamp: datetime               # Execution timestamp for this trade
    commission: float = 0.0
    tag: str = None                   # Optional tag inherited from order

# Example of how one might use default_factory for mutable defaults if needed,
# though not strictly necessary for the current definitions if None is acceptable.
# For example, if an Order should always have a list of child_orders:
# child_orders: list = field(default_factory=list)

# Similarly for timestamp, if it should always default to now() on creation:
# from datetime import timezone
# @dataclass
# class Order:
#     ...
#     timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
#     ...
# This is just for illustration; the current spec uses None as default for timestamps.

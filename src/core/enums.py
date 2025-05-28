from enum import Enum

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    STOP_MARKET = "STOP_MARKET"

class OrderStatus(Enum):
    PENDING = "PENDING"       # Order placed but not yet confirmed/rejected
    PENDING_OPEN = "PENDING_OPEN" # Order is pending submission or opening
    OPEN = "OPEN"           # Order acknowledged by exchange, not yet filled
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    COMPLETED = "COMPLETED" # Order is fully executed
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ACCEPTED = "ACCEPTED"   # Order is accepted by the broker, awaiting execution
    MODIFIED = "MODIFIED"   # Order has been modified
    TRIGGERED = "TRIGGERED" # Stop order has been triggered

class TradeType(Enum): # This is often used for the 'side' of a trade or signal
    BUY = "BUY"
    SELL = "SELL"

class OrderSide(Enum): # Adding OrderSide as it's commonly used and was missing
    BUY = "BUY"
    SELL = "SELL"
    # SHORT = "SHORT" # Depending on broker/requirements
    # COVER = "COVER" # Depending on broker/requirements

class InstrumentType(Enum):
    EQUITY = "EQUITY"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"

class Timeframe(Enum):
    TICK = "TICK"
    MINUTE_1 = "1MIN"
    MINUTE_3 = "3MIN"
    MINUTE_5 = "5MIN"
    MINUTE_15 = "15MIN"
    MINUTE_30 = "30MIN"
    HOUR_1 = "1H"
    DAY_1 = "1D"
    WEEK_1 = "1W"
    MONTH_1 = "1M"

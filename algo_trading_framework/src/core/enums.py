from enum import Enum

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(Enum):
    PENDING = "PENDING"       # Order placed but not yet confirmed/rejected
    OPEN = "OPEN"           # Order acknowledged by exchange, not yet filled
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"

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

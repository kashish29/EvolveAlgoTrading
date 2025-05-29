from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from src.core.models import Order
from src.core.enums import Timeframe

class BaseBrokerClient(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def get_balance(self):
        pass

    @abstractmethod
    def get_positions(self):
        pass

    @abstractmethod
    def get_order_book(self, symbol: str):
        pass

    @abstractmethod
    def get_order_history(self, order_id: Optional[str] = None, status: Optional[str] = None):
        pass

    @abstractmethod
    def get_trade_history(self, order_id: Optional[str] = None):
        pass

    @abstractmethod
    def place_order(self, order: Order):
        pass

    @abstractmethod
    def modify_order(self, order_id: str, new_price: Optional[float] = None, new_quantity: Optional[int] = None, new_trigger_price: Optional[float] = None):
        pass

    @abstractmethod
    def cancel_order(self, order_id: str):
        pass

    @abstractmethod
    def get_historical_candles(self, symbol: str, timeframe: Timeframe, from_date: datetime, to_date: datetime):
        pass

    @abstractmethod
    def get_current_bar(self, symbol: str):
        pass

    @abstractmethod
    def subscribe_market_data(self, symbols: list[str]):
        pass

    @abstractmethod
    def subscribe_order_updates(self):
        pass

from abc import ABC, abstractmethod
from datetime import datetime

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
    def get_order_history(self, order_id: str = None, status: str = None):
        pass

    @abstractmethod
    def get_trade_history(self, order_id: str = None):
        pass

    @abstractmethod
    def place_order(self, order: 'Order'):
        pass

    @abstractmethod
    def modify_order(self, order_id: str, new_price: float = None, new_quantity: int = None, new_trigger_price: float = None):
        pass

    @abstractmethod
    def cancel_order(self, order_id: str):
        pass

    @abstractmethod
    def get_historical_candles(self, symbol: str, timeframe: 'Timeframe', from_date: 'datetime', to_date: 'datetime'):
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

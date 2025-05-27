import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING: # pragma: no cover
    from src.broker_api.base_broker_client import BaseBrokerClient # type: ignore
    from src.core.models import Candle # type: ignore

class BaseStrategy(ABC):
    def __init__(self, strategy_id: str, broker: 'BaseBrokerClient', config: dict = None):
        self.strategy_id = strategy_id
        self.broker = broker # Instance of a class implementing BaseBrokerClient
        self.config = config or {}
        
        # Basic logging setup for the strategy
        self.logger = logging.getLogger(f"strategy.{self.strategy_id}")
        if not self.logger.handlers: # Avoid duplicate handlers if logger already configured
            # Default handler if no specific logging configuration is set up elsewhere
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO) # Default level
        self.logger.info(f"Strategy {self.strategy_id} initialized.")

    @abstractmethod
    def on_bar(self, current_bars: Dict[str, 'Candle']):
        """
        Called by the backtesting engine or live trading system on each new bar.
        
        :param current_bars: A dictionary mapping symbol strings to Candle objects 
                             representing the current market data for subscribed symbols.
        """
        pass

    # Optional helper methods can be added here
    # Example:
    # def place_market_order(self, symbol: str, quantity: int, side: 'OrderSide') -> tuple[str, str]:
    #     from src.core.models import Order, OrderType # Local import to avoid circular issues at module level
    #     order = Order(
    #         id=None, # Broker will assign
    #         symbol=symbol,
    #         quantity=quantity,
    #         side=side,
    #         order_type=OrderType.MARKET
    #     )
    #     order_id, status = self.broker.place_order(order)
    #     self.logger.info(f"Placed {side.value} {OrderType.MARKET.value} order for {quantity} {symbol}: {order_id} - Status: {status}")
    #     return order_id, status

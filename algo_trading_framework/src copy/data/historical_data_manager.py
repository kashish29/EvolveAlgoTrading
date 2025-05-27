import datetime
from typing import List, Dict, Tuple, Optional # Added Tuple and Optional for type hints

# Assuming models are in src.core.models
from src.core.models import Candle, Timeframe 

class HistoricalDataManager:
    def __init__(self, data: Optional[Dict[str, List[Candle]]] = None):
        # Data is a dict where key is symbol and value is a list of Candle objects, sorted by time
        self.data: Dict[str, List[Candle]] = data if data else {}
        self.all_candles_sorted: List[Candle] = [] # All candles from all symbols, sorted by timestamp

    def load_data(self, data_feeds: Dict[str, List[Candle]]):
        """
        Loads data feeds into the manager.
        data_feeds: A dictionary where keys are symbols and values are lists of Candle objects.
        """
        self.data = data_feeds
        # Combine and sort all candles for the engine's timeline iteration
        all_c: List[Candle] = []
        for symbol_candles in self.data.values():
            all_c.extend(symbol_candles)
        
        # Sort by timestamp, then by symbol (for consistent ordering if timestamps are the same)
        self.all_candles_sorted = sorted(all_c, key=lambda c: (c.timestamp, getattr(c, 'symbol', ''))) # getattr for safety if Candle might lack symbol

    def get_data(self, symbol: str, timeframe: Timeframe, from_date: datetime.datetime, to_date: datetime.datetime) -> List[Candle]:
        """
        Simple implementation: filter pre-loaded data for a specific symbol and date range.
        Timeframe is part of the signature but ignored in this basic version, assuming data is pre-filtered by timeframe.
        """
        # The timeframe parameter is present for API consistency but not used in this simple filter.
        # A more advanced version would handle resampling or loading specific timeframe data.
        symbol_data = self.data.get(symbol, [])
        return [c for c in symbol_data if from_date <= c.timestamp <= to_date]

    def get_all_data_sorted_by_timestamp(self) -> List[Tuple[datetime.datetime, Dict[str, Candle]]]:
        """
        Transforms the loaded candle data into a timeline format suitable for BacktesterEngine.
        Returns a list of tuples: (timestamp, {symbol: Candle_at_that_timestamp}).
        Candles must have a 'symbol' attribute for this method to work correctly.
        """
        timeline: Dict[datetime.datetime, Dict[str, Candle]] = {}
        for candle in self.all_candles_sorted:
            candle_symbol = getattr(candle, 'symbol', None)
            if candle_symbol is None:
                # Log or handle candles without symbols if necessary
                continue 

            if candle.timestamp not in timeline:
                timeline[candle.timestamp] = {}
            timeline[candle.timestamp][candle_symbol] = candle
        
        # Sort timeline by timestamp
        sorted_timeline: List[Tuple[datetime.datetime, Dict[str, Candle]]] = sorted(timeline.items())
        return sorted_timeline

    def get_bar_at(self, symbol: str, timestamp: datetime.datetime, timeframe: Optional[Timeframe] = None) -> Optional[Candle]:
        """
        Helper to get a specific bar for a symbol at a given timestamp.
        Timeframe is optional and ignored in this basic implementation.
        """
        # This is a simple lookup. A real implementation might need to be more complex,
        # e.g., finding the bar that contains the timestamp for a given timeframe.
        symbol_data = self.data.get(symbol, [])
        for candle in symbol_data:
            if candle.timestamp == timestamp:
                return candle
        return None

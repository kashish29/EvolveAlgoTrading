import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime

# For a more sophisticated cache, libraries like 'cachetools' could be used
# for LRU, TTL, and other eviction policies.
# This implementation is a simple in-memory dictionary-based cache.

class DataCache:
    """
    A simple in-memory cache for storing and retrieving Pandas DataFrames.
    Keys are strings, typically generated from data request parameters
    (symbol, dates, timeframe).
    """

    def __init__(self, max_size: Optional[int] = None):
        """
        Initializes the DataCache.

        Args:
            max_size (Optional[int]): The maximum number of items to store in the cache.
                                      If None, the cache has no size limit (can grow indefinitely).
                                      If set, a simple FIFO eviction policy is used when the limit is reached.
                                      Note: For production, a more robust cache (e.g. LRU) might be needed.
        """
        self._cache: Dict[str, pd.DataFrame] = {}
        self._keys_order: list[str] = [] # To maintain order for FIFO eviction if max_size is set
        self.max_size = max_size
        print(f"DataCache initialized with max_size: {'unlimited' if max_size is None else max_size}.")

    def _evict_if_needed(self):
        """Evicts the oldest item if the cache exceeds max_size."""
        if self.max_size is not None and len(self._cache) > self.max_size:
            oldest_key = self._keys_order.pop(0) # Remove the oldest key from tracking list
            if oldest_key in self._cache:
                del self._cache[oldest_key] # Remove from cache
                print(f"DataCache: Evicted '{oldest_key}' due to cache size limit ({self.max_size}).")


    def get_data(self, key: str) -> Optional[pd.DataFrame]:
        """
        Retrieves data from the cache.

        Args:
            key (str): The cache key associated with the data.

        Returns:
            Optional[pd.DataFrame]: The cached DataFrame if found, otherwise None.
        """
        if key in self._cache:
            print(f"DataCache: Cache hit for key '{key}'.")
            # If implementing LRU, this is where you'd update the key's freshness.
            # For FIFO, no action needed on get.
            return self._cache[key].copy() # Return a copy to prevent modification of cached DataFrame
        else:
            print(f"DataCache: Cache miss for key '{key}'.")
            return None

    def store_data(self, key: str, data: pd.DataFrame):
        """
        Stores data in the cache.

        Args:
            key (str): The cache key to associate with the data.
            data (pd.DataFrame): The DataFrame to store. It should not be empty.
        """
        if not isinstance(data, pd.DataFrame):
            print(f"DataCache Error: Attempted to store non-DataFrame data for key '{key}'. Data not stored.")
            return
            
        if data.empty:
            # Policy decision: Do we cache empty DataFrames?
            # Caching empty results might be useful to avoid re-fetching if a source consistently returns no data.
            # For now, let's assume we only cache non-empty DataFrames to save space,
            # but this could be configurable.
            print(f"DataCache: Data for key '{key}' is an empty DataFrame. Not caching.")
            return

        if key in self._cache:
            # Data for key already exists, update it.
            # For FIFO, remove old key from order list first if it's being updated.
            if key in self._keys_order: # Should always be true if max_size is used
                 self._keys_order.remove(key)
        
        self._cache[key] = data.copy() # Store a copy
        self._keys_order.append(key) # Add/move key to end of list (most recent)
        
        print(f"DataCache: Stored data for key '{key}'. Current cache size: {len(self._cache)}.")
        
        self._evict_if_needed() # Check and evict if cache is over size limit

    def clear(self):
        """Clears all items from the cache."""
        self._cache.clear()
        self._keys_order.clear()
        print("DataCache: Cache cleared.")

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        return key in self._cache
        
    def __repr__(self) -> str:
        return f"<DataCache(size={len(self._cache)}, max_size={self.max_size if self.max_size is not None else 'unlimited'})>"

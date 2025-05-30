import unittest
import pandas as pd
from typing import Dict # Keep Dict for type hinting if needed, though not strictly in test logic

from src.data_handler.data_cache import DataCache

class TestDataCache(unittest.TestCase):

    def setUp(self):
        self.cache_limited = DataCache(max_size=3) # Cache for testing eviction
        self.cache_unlimited = DataCache(max_size=None) # Cache for testing no limit
        
        self.sample_df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        self.sample_df2 = pd.DataFrame({'X': [10, 20], 'Y': [30, 40]})
        self.sample_df3 = pd.DataFrame({'P': [5, 6], 'Q': [7, 8]})
        self.sample_df4 = pd.DataFrame({'M': [9, 0], 'N': [1, 2]}) # Another distinct df
        self.empty_df = pd.DataFrame()

    def test_store_and_get_data_success(self):
        self.cache_unlimited.store_data("key1", self.sample_df1)
        retrieved_df = self.cache_unlimited.get_data("key1")
        
        self.assertIsNotNone(retrieved_df)
        pd.testing.assert_frame_equal(retrieved_df, self.sample_df1)
        # Check if it's a copy
        self.assertNotEqual(id(retrieved_df), id(self.sample_df1), "Cache should return a copy of the DataFrame.")

    def test_get_data_miss(self):
        retrieved_df = self.cache_unlimited.get_data("non_existent_key")
        self.assertIsNone(retrieved_df)

    def test_store_data_overwrite_existing_key(self):
        self.cache_unlimited.store_data("key1", self.sample_df1)
        # Store different data with the same key
        self.cache_unlimited.store_data("key1", self.sample_df2) 
        
        retrieved_df = self.cache_unlimited.get_data("key1")
        pd.testing.assert_frame_equal(retrieved_df, self.sample_df2)
        self.assertEqual(len(self.cache_unlimited), 1)

    def test_store_empty_dataframe_policy(self):
        # DataCache current policy: do not store empty DataFrames
        self.cache_unlimited.store_data("empty_key", self.empty_df)
        self.assertIsNone(self.cache_unlimited.get_data("empty_key"))
        self.assertEqual(len(self.cache_unlimited), 0)

    def test_store_non_dataframe_data_policy(self):
        # DataCache current policy: do not store non-DataFrame objects
        non_df_data = {"value": 100} 
        # Type checking would catch this, but testing runtime robustness
        # The following line will cause a mypy error if type hints are checked,
        # but for runtime test, it proceeds. CSVDataSource expects pd.DataFrame.
        self.cache_unlimited.store_data("non_df_key", non_df_data) # type: ignore 
        self.assertIsNone(self.cache_unlimited.get_data("non_df_key"))
        self.assertEqual(len(self.cache_unlimited), 0)

    def test_cache_max_size_and_fifo_eviction(self):
        cache = self.cache_limited # Use the size-limited cache
        self.assertEqual(cache.max_size, 3)

        # Store 3 items: cache is full
        cache.store_data("k1", self.sample_df1) # Oldest
        cache.store_data("k2", self.sample_df2)
        cache.store_data("k3", self.sample_df3) # Newest
        self.assertEqual(len(cache), 3)
        self.assertIn("k1", cache)
        self.assertIn("k2", cache)
        self.assertIn("k3", cache)

        # Store 4th item: "k1" (oldest) should be evicted
        cache.store_data("k4", self.sample_df4) 
        self.assertEqual(len(cache), 3) # Size remains 3
        self.assertNotIn("k1", cache)   # k1 evicted
        self.assertIn("k2", cache)
        self.assertIn("k3", cache)
        self.assertIn("k4", cache)    # k4 added

        # Accessing k2 (via get_data) does not change FIFO order
        cache.get_data("k2") 

        # Store 5th item: "k2" (now oldest among k2, k3, k4) should be evicted
        cache.store_data("k5", self.sample_df1) # Re-using df1 with a new key
        self.assertEqual(len(cache), 3)
        self.assertNotIn("k2", cache)   # k2 evicted
        self.assertIn("k3", cache)
        self.assertIn("k4", cache)
        self.assertIn("k5", cache)    # k5 added

    def test_cache_eviction_with_key_update_becomes_newest_fifo(self):
        cache = self.cache_limited
        cache.store_data("key_A", self.sample_df1) # Oldest
        cache.store_data("key_B", self.sample_df2)
        cache.store_data("key_C", self.sample_df3) # Newest. Order: A, B, C

        # Update "key_A" with new data. It should become the newest.
        cache.store_data("key_A", self.sample_df4) # Order: B, C, A (A is now newest)
        self.assertEqual(len(cache), 3)
        pd.testing.assert_frame_equal(cache.get_data("key_A"), self.sample_df4)

        # Add another item, "key_B" (now oldest) should be evicted
        cache.store_data("key_D", self.sample_df2) # Order: C, A, D
        self.assertNotIn("key_B", cache)
        self.assertIn("key_C", cache)
        self.assertIn("key_A", cache) # Still contains the updated key_A
        self.assertIn("key_D", cache)
        self.assertEqual(len(cache), 3)

    def test_cache_with_no_max_size_limit(self):
        cache = self.cache_unlimited
        for i in range(5): # Store 5 items
            cache.store_data(f"item_key_{i}", self.sample_df1)
        self.assertEqual(len(cache), 5) # All 5 items should be present

    def test_clear_cache(self):
        self.cache_limited.store_data("d1", self.sample_df1)
        self.cache_limited.store_data("d2", self.sample_df2)
        self.assertGreater(len(self.cache_limited), 0)
        
        self.cache_limited.clear()
        self.assertEqual(len(self.cache_limited), 0)
        self.assertIsNone(self.cache_limited.get_data("d1"))
        self.assertIsNone(self.cache_limited.get_data("d2"))
        # Also check internal _keys_order list is cleared
        self.assertEqual(len(self.cache_limited._keys_order), 0)


    def test_contains_dunder_method(self):
        self.cache_unlimited.store_data("mykey", self.sample_df1)
        self.assertTrue("mykey" in self.cache_unlimited) # Calls __contains__
        self.assertFalse("non_key" in self.cache_unlimited)

if __name__ == '__main__':
    unittest.main()

import time
import threading
import random
import re
from collections import OrderedDict
import heapq
import logging
import gc
import weakref
from typing import Literal,Optional
import sys
from pympler import asizeof

class Redis:
    UNIT_MULTIPLIERS = {
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3
    }
    def __init__(self, max_size=512, unit: Optional[Literal['KB', 'MB', 'GB']] = 'MB', default_expiration_time=3600, cleanup_interval=10, cleanup_fraction=0.25, verbose=False, cleanup_strategy:Optional[Literal['LRU','LFU','FIFO','SizeBased','Random']]='LRU'):
        if unit not in self.UNIT_MULTIPLIERS:
            raise ValueError(f"Invalid unit '{unit}'. Use 'KB', 'MB', or 'GB'.")
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.max_size = max_size * self.UNIT_MULTIPLIERS[unit]
        self.default_expiration_time = default_expiration_time
        self.cleanup_interval = cleanup_interval
        self.cleanup_fraction = cleanup_fraction
        self.expiration_heap = []
        self.verbose = verbose
        self.cleanup_loop_thread =True
        self.cleanup_strategy = cleanup_strategy
        self.access_frequency = {}

        if self.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.ERROR)

        self._start_cleanup_thread()
        
    def __enter__(self):
        return self
    
    def close(self):
        self.cleanup_loop_thread = False
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def _get_size(self, obj):
        """使用 pympler.asizeof() 計算物件大小，忽略不支持的類型。"""
        try:
            return asizeof.asizeof(obj)
        except TypeError as e:
            # 忽略 '_EmptyListener' 相關的錯誤，不記錄日志
            if 'cannot create weak reference to \'_EmptyListener\'' in str(e):
                return 0
            # 記錄其他 TypeError 錯誤
            logging.warning(f"Error calculating size of object: {e}. Returning 0 size.")
            return 0
        except Exception as e:
            # 記錄其他非預期的錯誤
            logging.error(f"Unexpected error calculating size of object: {e}. Returning 0 size.")
            return 0

    def _get_current_size(self):
        """Get the total size of all cache entries."""
        total_size = 0
        with self.lock:
            for k, v in self.cache.items():
                total_size += self._get_size(k) + self._get_size(v[0])  # Include only the value's size
        return total_size

    def _cleanup(self):
        current_time = time.time()
        with self.lock:
            # Remove expired items
            while self.expiration_heap and self.expiration_heap[0][0] < current_time:
                _, key = heapq.heappop(self.expiration_heap)
                if key in self.cache and not self.cache[key][3]:  # Check if key is still in cache and not permanent
                    del self.cache[key]
                    logging.debug(f"Cleaned up expired key: {key}")

            if self.cleanup_strategy == 'LRU':
                self._cleanup_lru()
            elif self.cleanup_strategy == 'LFU':
                self._cleanup_lfu()
            elif self.cleanup_strategy == 'FIFO':
                self._cleanup_fifo()
            elif self.cleanup_strategy == 'SizeBased':
                self._cleanup_size_based()
            elif self.cleanup_strategy == 'Random':
                self._cleanup_random()
                        
    def _cleanup_lru(self):
        # Remove the least recently used items
        if len(self.cache) > self.max_size * self.cleanup_fraction:
            num_to_delete = int(len(self.cache) * self.cleanup_fraction)
            for _ in range(num_to_delete):
                key, _ = self.cache.popitem(last=False)
                logging.debug(f"LRU Cleaned: {key}")

    def _cleanup_lfu(self):
        # Remove the least frequently used items
        if len(self.cache) > self.max_size * self.cleanup_fraction:
            num_to_delete = int(len(self.cache) * self.cleanup_fraction)
            # Sort by access frequency
            least_used_keys = sorted(self.access_frequency, key=self.access_frequency.get)[:num_to_delete]
            for key in least_used_keys:
                if key in self.cache:
                    del self.cache[key]
                    del self.access_frequency[key]
                    logging.debug(f"LFU Cleaned: {key}")

    def _cleanup_fifo(self):
        # Remove the first items that were added
        if len(self.cache) > self.max_size * self.cleanup_fraction:
            num_to_delete = int(len(self.cache) * self.cleanup_fraction)
            for _ in range(num_to_delete):
                key, _ = self.cache.popitem(last=False)  # FIFO is similar to LRU if you remove from the front
                logging.debug(f"FIFO Cleaned: {key}")

    def _cleanup_size_based(self):
        # Remove items based on size, e.g., largest first
        if len(self.cache) > self.max_size * self.cleanup_fraction:
            num_to_delete = int(len(self.cache) * self.cleanup_fraction)
            # Sort by size (largest first)
            sorted_items = sorted(self.cache.items(), key=lambda item: len(str(item[0])) + len(str(item[1][0])), reverse=True)
            for i in range(num_to_delete):
                key = sorted_items[i][0]
                del self.cache[key]
                logging.debug(f"SizeBased Cleaned: {key}")

    def _cleanup_random(self):
        # Randomly remove items
        if len(self.cache) > self.max_size * self.cleanup_fraction:
            num_to_delete = int(len(self.cache) * self.cleanup_fraction)
            keys_to_delete = random.sample(list(self.cache.keys()), num_to_delete)
            for key in keys_to_delete:
                if key in self.cache:
                    del self.cache[key]
                    logging.debug(f"Randomly Cleaned: {key}")

    def _start_cleanup_thread(self):
        def cleanup_loop():
            while self.cleanup_loop_thread:
                logging.debug(f"Waiting for cleanup interval: {self.cleanup_interval} seconds")
                time.sleep(self.cleanup_interval)
                start_time = time.time()
                self._cleanup()
                end_time = time.time()
                collected = gc.collect()
                logging.debug("Garbage collector: collected %d objects in %.2f seconds." % (collected, end_time - start_time))
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()

    def _evict_if_needed(self, new_entry_size):
        evicted_any = False
        with self.lock:
            for _ in range(len(self.cache)):
                if self._get_current_size() + new_entry_size <= self.max_size:
                    break
                key, value = next(iter(self.cache.items()))
                if not value[3]:  # 如果該項目不是永久的，則移除
                    if self.cleanup_strategy == 'LRU':
                        key, _ = self.cache.popitem(last=False)
                    elif self.cleanup_strategy == 'LFU':
                        least_used_key = min(self.access_frequency, key=self.access_frequency.get)
                        self.cache.pop(least_used_key, None)
                        self.access_frequency.pop(least_used_key, None)
                    elif self.cleanup_strategy == 'FIFO':
                        key, _ = self.cache.popitem(last=False)
                    elif self.cleanup_strategy == 'SizeBased':
                        largest_key = max(self.cache, key=lambda k: self._get_size(k) + self._get_size(self.cache[k][0]))
                        self.cache.pop(largest_key, None)
                    elif self.cleanup_strategy == 'Random':
                        random_key = random.choice(list(self.cache.keys()))
                        self.cache.pop(random_key, None)
                    else:
                        # Default to LRU if no strategy matches
                        key, _ = self.cache.popitem(last=False)
                    logging.debug(f"Evicted: {key}")
                    evicted_any = True
                else:
                    self.cache.move_to_end(key)
                logging.debug(f"Evicting... Current Cache Size: {self._get_current_size()}")
        return evicted_any

    def set(self, key, value, expiration_time=None, permanent=False, use_weakref=False):
        if expiration_time is None:
            expiration_time = self.default_expiration_time
        with self.lock:
            entry_size = self._get_size(key) + self._get_size(value)  # 使用 _get_size 計算大小
            current_size = self._get_current_size()
            logging.debug(f"Attempting to set {key} with size {entry_size}. Current cache size: {current_size}, Max size: {self.max_size}")
            
            if entry_size > self.max_size:
                logging.debug(f"Warning: Entry size for {key} is too large, cannot fit into the cache")
                return
            
            while current_size + entry_size > self.max_size:
                if not self.cache or not self._evict_if_needed(entry_size):
                    logging.debug(f"Warning: Cannot evict enough space for {key}. All items are permanent.")
                    return
                current_size = self._get_current_size()
                
            if use_weakref:
                value = weakref.ref(value)
                
            self.cache[key] = (value, expiration_time, time.time(), permanent)
            if not permanent:
                heapq.heappush(self.expiration_heap, (time.time() + expiration_time, key))
            self.cache.move_to_end(key)  # Move the new item to the end
            
            # 根據策略更新訪問和排序資訊
            if self.cleanup_strategy == 'LFU':
                # 初始化訪問次數為 0
                self.access_frequency[key] = 0
            elif self.cleanup_strategy == 'LRU':
                # 將項目移到尾部，標記為最近使用
                self.cache.move_to_end(key)
            elif self.cleanup_strategy == 'FIFO':
                # FIFO 順序由 OrderedDict 自動維持
                pass
            elif self.cleanup_strategy == 'SizeBased':
                # SizeBased 會在清理時處理，不需要在 set 時更新
                pass
            elif self.cleanup_strategy == 'Random':
                # Random 策略不需特殊處理
                pass
            
            logging.debug(f"Set: {key} - Current Cache Size: {self._get_current_size()}")

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                logging.debug(f"Get: {key} - Cache miss")
                return None
            
            # 取得快取項目
            value_tuple = self.cache[key]
            current_time = time.time()
            
            # 檢查項目是否過期且不是永久性
            if current_time - value_tuple[2] > value_tuple[1] and not value_tuple[3]:
                del self.cache[key]
                if key in self.access_frequency:
                    del self.access_frequency[key]
                logging.debug(f"Get: {key} - Item expired")
                return None
            
            # 更新策略相關資料
            if self.cleanup_strategy == 'LFU':
                # 更新訪問頻率
                self.access_frequency[key] = self.access_frequency.get(key, 0) + 1
            elif self.cleanup_strategy == 'LRU':
                # 更新最近使用順序
                self.cache.move_to_end(key)
            
            # 如果項目為弱參考，檢查其是否已被回收
            value = value_tuple[0]
            if isinstance(value, weakref.ReferenceType):
                value = value()
            
            logging.debug(f"Get: {key} - Cache hit")
            return value

    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logging.debug(f"Delete: {key}")
            # Remove from frequency map if using LFU
                if key in self.access_frequency:
                    del self.access_frequency[key]
                
    def expire_matching_keys(self, pattern):
        with self.lock:
            regex = re.compile(pattern)
            keys_to_expire = [key for key in self.cache.keys() if regex.match(key)]
            for key in keys_to_expire:
                if key in self.cache:
                    self.cache[key] = (self.cache[key][0], 0, time.time(), self.cache[key][3])
                    logging.debug(f"Expired key: {key}")

def test():
    # 測試設置不同的大小限制單位
    print("Testing different size units (KB, MB, GB)...")
    cache_kb = Redis(max_size=1, unit='KB', verbose=True)  # 設置最大大小為1 KB
    cache_mb = Redis(max_size=1, unit='MB', verbose=True)  # 設置最大大小為1 MB
    cache_gb = Redis(max_size=1, unit='GB', verbose=True)  # 設置最大大小為1 GB

    # 檢查基礎設定是否正確
    assert cache_kb.max_size == 1024, "Max size for KB should be 1024 bytes."
    assert cache_mb.max_size == 1024**2, "Max size for MB should be 1 MB in bytes."
    assert cache_gb.max_size == 1024**3, "Max size for GB should be 1 GB in bytes."
    
    cache_kb.close()
    cache_mb.close()
    cache_gb.close()

    print("Passed size unit tests.\n")

    # 測試過期項目和清理策略
    print("Testing expiration and cleanup strategies...")
    cache = Redis(max_size=0.0001, unit='MB', default_expiration_time=3, cleanup_interval=1, cleanup_fraction=0.5, verbose=True)  # 設置最大大小為0.0001 MB（100字節），默認過期時間為3秒

    cache.set('key1', 'value1')
    time.sleep(1)
    assert cache.get('key1') == 'value1', "Expected key1 to be present."
    
    time.sleep(4)  # 等待超過默認過期時間
    assert cache.get('key1') is None, "Expected key1 to be expired."

    print("Passed expiration tests.\n")

    # 測試永久性項目
    print("Testing permanent items...")
    cache.set('key2', 'value2', permanent=True)
    time.sleep(4)
    assert cache.get('key2') == 'value2', "Expected key2 to be permanent and not expired."
    
    cache.close()

    print("Passed permanent item tests.\n")

    # 測試清理策略：LRU
    print("Testing LRU cleanup strategy...")
    cache = Redis(max_size=1, unit='KB', cleanup_strategy='LRU', verbose=True)
    cache.set('key1', 'v' * 512)
    cache.set('key2', 'v' * 512)  # 應該觸發 LRU 驅逐 key1

    assert cache.get('key1') is None, "Expected key1 to be evicted by LRU."
    assert cache.get('key2') == 'v' * 512, "Expected key2 to be present."

    cache.close()
    
    print("Passed LRU cleanup tests.\n")

    # 測試清理策略：LFU
    print("Testing LFU cleanup strategy...")
    cache = Redis(max_size=1, unit='KB', cleanup_strategy='LFU', verbose=True)
    cache.set('key1', 'v' * 300)
    cache.set('key2', 'v' * 500)
    cache.get('key1')  # 訪問 key1 增加其使用次數
    cache.set('key3', 'v' * 300)  # 應該觸發 LFU 驅逐 key2

    assert cache.get('key1') == 'v' * 300, "Expected key1 to remain (frequently used)."
    assert cache.get('key2') is None, "Expected key2 to be evicted by LFU."
    assert cache.get('key3') == 'v' * 300, "Expected key3 to be present."

    cache.close()
    
    print("Passed LFU cleanup tests.\n")

    # 測試清理策略：FIFO
    print("Testing FIFO cleanup strategy...")
    cache = Redis(max_size=1, unit='KB', cleanup_strategy='FIFO', verbose=True)
    cache.set('key1', 'v' * 600)
    cache.set('key2', 'v' * 300)
    cache.set('key3', 'v' * 300)  # 應該觸發 FIFO 驅逐 key1

    assert cache.get('key1') is None, "Expected key1 to be evicted by FIFO."
    assert cache.get('key2') == 'v' * 300, "Expected key2 to be present."
    assert cache.get('key3') == 'v' * 300, "Expected key3 to be present."

    cache.close()
    
    print("Passed FIFO cleanup tests.\n")

    # 測試清理策略：SizeBased
    print("Testing SizeBased cleanup strategy...")
    cache = Redis(max_size=1, unit='KB', cleanup_strategy='SizeBased', verbose=True)
    cache.set('key1', 'v' * 900)
    cache.set('key2', 'v' * 200)  # 應該觸發 SizeBased 清理 key1（較大）

    assert cache.get('key1') is None, "Expected key1 to be evicted by SizeBased."
    assert cache.get('key2') == 'v' * 200, "Expected key2 to be present."

    cache.close()
    
    print("Passed SizeBased cleanup tests.\n")

    # 測試清理策略：Random
    print("Testing Random cleanup strategy...")
    cache = Redis(max_size=1, unit='KB', cleanup_strategy='Random', verbose=True)
    cache.set('key1', 'v' * 500)
    cache.set('key2', 'v' * 500)
    cache.set('key3', 'v' * 500)  # 應該隨機移除一個項目

    evicted_key = None
    if cache.get('key1') is None:
        evicted_key = 'key1'
    elif cache.get('key2') is None:
        evicted_key = 'key2'
    elif cache.get('key3') is None:
        evicted_key = 'key3'

    assert evicted_key is not None, "Expected one key to be randomly evicted."
    assert (cache.get('key1') is not None or cache.get('key2') is not None or cache.get('key3') is not None), "Expected at least two keys to remain."

    cache.close()
    
    print("Passed Random cleanup tests.\n")

    print("All tests passed!")

if __name__ == "__main__":
    test()


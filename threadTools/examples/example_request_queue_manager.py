import logging
import threading
from utils.request_queue_manager import RequestQueueManager

def main():
    # Example usage of RequestQueueManager
    # 創建一個 RequestQueueManager 的實例
    queue_manager = RequestQueueManager()

    def process_request(key):
        queue_manager.inqueue(key)
        print(f"Processing {key}")
        # 模擬處理時間
        import time
        time.sleep(2)
        queue_manager.dequeue(key)
        print(f"Finished processing {key}")

    keys = ["AAPL", "AAPL", "GOOG", "AAPL", "GOOG"]
    threads = []

    for key in keys:
        thread = threading.Thread(target=process_request, args=(key,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
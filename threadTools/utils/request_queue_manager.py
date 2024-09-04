import threading

class RequestQueueManager:
    def __init__(self):
        self.active_requests = {}
        self.condition_locks = {}
        self.global_lock = threading.Lock()

    def get_condition(self, request_key):
        with self.global_lock:
            if request_key not in self.condition_locks:
                self.condition_locks[request_key] = threading.Condition()
            return self.condition_locks[request_key]

    def inqueue(self, request_key):
        condition = self.get_condition(request_key)
        with condition:
            while request_key in self.active_requests:
                condition.wait()  # 只等待相同 request_key 的 Condition
            self.active_requests[request_key] = True

    def dequeue(self, request_key):
        condition = self.get_condition(request_key)
        with condition:
            if request_key in self.active_requests:
                del self.active_requests[request_key]
                condition.notify_all()  # 喚醒等待這個 request_key 的線程

        with self.global_lock:
            # 清理不再需要的 condition_locks
            if request_key in self.condition_locks and not self.active_requests.get(request_key):
                del self.condition_locks[request_key]
import threading

# Semaphore class for managing access to shared resources
class Semaphore:
    def __init__(self, initial):
        self.lock = threading.Lock()
        self.value = initial
        self.condition = threading.Condition(self.lock)

    def acquire(self):
        with self.condition:
            while self.value == 0:
                self.condition.wait()
            self.value -= 1

    def release(self):
        with self.condition:
            self.value += 1
            self.condition.notify()
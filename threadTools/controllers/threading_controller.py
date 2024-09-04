import logging
import threading
from typing import List, Callable, Any

# MyThread and MultiThreadManager for managing threads
class MyThread(threading.Thread):
    def __init__(self, index, func, args=(), kwargs={}, verbose=False):
        super(MyThread, self).__init__()
        self.index = index
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.exception = None
        self.verbose = verbose

    def run(self):
        if self.verbose:
            logging.info(f"Thread {self.index} started.")
        try:
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
        if self.verbose:
            logging.info(f"Thread {self.index} finished.")
            
class MultiThreadManager:
    def __init__(self, verbose=False):
        self.threads = []
        self.verbose = verbose

    def add_thread(self, func, args=(), kwargs={}):
        index = len(self.threads)  # Current thread index
        thread = MyThread(index, func, args, kwargs, verbose=self.verbose)
        self.threads.append(thread)
        return thread

    def start_threads(self):
        if self.verbose:
            logging.info("Starting all threads.")
        for thread in self.threads:
            thread.start()

    def wait_for_threads(self):
        for thread in self.threads:
            thread.join()
        if self.verbose:
            logging.info("All threads have completed.")

    def get_results_in_order(self):
        """Get results and exceptions from threads in order"""
        if self.verbose:
            logging.info("Collecting results from threads.")
        self.wait_for_threads()
        results = [None] * len(self.threads)
        exceptions = []

        for thread in self.threads:
            if thread.exception is not None:
                exceptions.append((thread.index, thread.exception))
                if self.verbose:
                    logging.error(f"Exception from thread {thread.index}: {thread.exception}")
            else:
                results[thread.index] = thread.result
                if self.verbose:
                    logging.info(f"Result collected from thread {thread.index}.")

        if exceptions:
            exceptions.sort(key=lambda x: x[0])
            if self.verbose:
                logging.info("Exceptions sorted by index.")
            return (results, [ex[1] for ex in exceptions])
        if self.verbose:
            logging.info("All results collected with no exceptions.")
        return (results, None)
import threading
import logging
import time
from utils.semaphore import Semaphore

def main():
    #Example usage of Semaphore
    def worker(semaphore, worker_id):
        logging.info(f"Worker {worker_id} is waiting to acquire semaphore")
        semaphore.acquire()
        try:
            logging.info(f"Worker {worker_id} has acquired semaphore")
            # Simulate some work with the shared resource
            time.sleep(2)
            logging.info(f"Worker {worker_id} is releasing semaphore")
        finally:
            semaphore.release()

    num_workers = 5
    max_concurrent_workers = 2

    semaphore = Semaphore(max_concurrent_workers)
    threads = []

    for i in range(num_workers):
        thread = threading.Thread(target=worker, args=(semaphore, i))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logging.info("All workers have completed their tasks")
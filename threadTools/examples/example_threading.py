import logging
import time
from controllers.threading_controller import MultiThreadManager

def main():
    # Example usage of MultiThreadManager
    def example_task_thread(data):
        time.sleep(2)
        return data ** 2

    manager = MultiThreadManager(verbose=True)
    for i in range(5):
        manager.add_thread(example_task_thread, (i,))

    manager.start_threads()
    results, exceptions = manager.get_results_in_order()

    if exceptions:
        logging.error(f"Exceptions occurred: {exceptions}")
    logging.info(f"Results: {results}")
import logging
import multiprocessing
from typing import List, Callable, Any, Tuple

# Multiprocessing Manager
class MultiprocessingController:
    """method must be put at the toppest level of the module
    """
    def __init__(self, verbose: bool = False):
        self.tasks: List[Tuple[Callable, Tuple[Any, ...]]] = []
        self.processes: List[multiprocessing.Process] = []
        self.verbose = verbose

    def log(self, message: str, level=logging.INFO):
        if self.verbose:
            logging.log(level, message)

    def add_task(self, func: Callable, *args: Any) -> None:
        """Add a function and its arguments to the controller"""
        self.tasks.append((func, args))
        if self.verbose:
            logging.info(f'Added task: {func.__name__} with arguments: {args}')

    def run_tasks(self) -> None:
        """Run all tasks in separate processes"""
        self.processes = []  # Clear the previous processes list
        for func, args in self.tasks:
            p = multiprocessing.Process(target=func, args=args, name=f"{func.__name__}({args})")
            self.processes.append(p)
            if self.verbose:
                logging.info(f'Starting process: {p.name}')
            p.start()

    def monitor_tasks(self) -> None:
        """Monitor the processes"""
        try:
            while True:
                alive_processes = [p for p in self.processes if p.is_alive()]
                if self.verbose:
                    logging.info(f"Alive processes: {len(alive_processes)}")
                if not alive_processes:
                    break
                for p in alive_processes:
                    p.join(timeout=1)
        except KeyboardInterrupt:
            if self.verbose:
                logging.info("Monitoring interrupted by user.")
            self.terminate_tasks()

    def terminate_tasks(self) -> None:
        """Terminate all running processes"""
        for p in self.processes:
            if p.is_alive():
                p.terminate()
                if self.verbose:
                    logging.info(f'Terminated process: {p.name}')
        self.processes = [p for p in self.processes if p.is_alive()]
        
def example_task_for_multiprocessing(name: str, duration: int) -> None:
    import time
    logging.info(f"Task {name} started")
    time.sleep(duration)
    logging.info(f"Task {name} finished")
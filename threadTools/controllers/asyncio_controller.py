import asyncio
import logging
from typing import List, Callable, Any, Tuple

# AsyncioController for managing asyncio tasks
class AsyncioController:
    def __init__(self, verbose: bool = False):
        self.coros: List[Tuple[Callable, Tuple[Any, ...]]] = []
        self.tasks: List[asyncio.Task] = []
        self.verbose = verbose
        self.stop = False

    def add_task(self, coro: Callable, *args: Any) -> None:
        """Add a coroutine function and its arguments to the controller"""
        self.coros.append((coro, args))
        if self.verbose:
            logging.info(f'Added task: {coro.__name__} with arguments: {args}')

    async def run_tasks(self) -> None:
        """Run single or multiple tasks"""
        self.tasks = []  # Clear the previous tasks list
        for coro, args in self.coros:
            task = asyncio.create_task(coro(*args), name=f"{coro.__name__}({args})")
            self.tasks.append(task)
            if self.verbose:
                logging.info(f'Running task: {task.get_name()}')
        await asyncio.gather(*self.tasks)
        if self.verbose:
            logging.info('All tasks have been completed.')

    async def monitor_tasks(self) -> None:
        """Monitor the tasks"""
        while not self.stop:
            pending = [task for task in self.tasks if not task.done()]
            if self.verbose:
                logging.info(f"Pending tasks: {len(pending)}")
            if not pending:
                break
            await asyncio.sleep(1)

    def cancel_tasks(self, tasks: List[asyncio.Task] = None) -> None:
        """Cancel single or multiple tasks"""
        if tasks is None:
            tasks = self.tasks
        for task in tasks:
            task.cancel()
            if self.verbose:
                logging.info(f'Cancelled task: {task.get_name()}')
        self.tasks = [task for task in self.tasks if not task.done()]

    def stop_monitoring(self) -> None:
        """Stop the monitoring of tasks"""
        self.stop = True
        if self.verbose:
            logging.info('Stopped monitoring tasks.')
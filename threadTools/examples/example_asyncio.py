import asyncio
import logging
from controllers.asyncio_controller import AsyncioController

# Example usage of AsyncioController
async def example_task(name: str, duration: int) -> None:
    try:
        logging.info(f"Task {name} started")
        await asyncio.sleep(duration)
        logging.info(f"Task {name} finished")
    except asyncio.CancelledError:
        logging.info(f"Task {name} was cancelled")

async def main_asyncio():
    controller = AsyncioController(verbose=True)
    
    # Add tasks
    controller.add_task(example_task, "A", 5)
    controller.add_task(example_task, "B", 10)
    controller.add_task(example_task, "C", 15)

    # Run all tasks
    run_task = asyncio.create_task(controller.run_tasks())
    
    # Monitor tasks
    monitor_task = asyncio.create_task(controller.monitor_tasks())
    
    # Wait for a while then stop monitoring and cancel tasks
    await asyncio.sleep(7)
    controller.stop_monitoring()
    await monitor_task  # Ensure monitoring has stopped
    controller.cancel_tasks()
    
    # Wait for the run task to finish
    await run_task
    
if __name__ == "__main__":
    asyncio.run(main_asyncio())
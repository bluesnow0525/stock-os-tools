import logging
from controllers.multiprocessing_controller import MultiprocessingController, example_task_for_multiprocessing

def main():
    # Example usage of Multiprocessing
    controller = MultiprocessingController(verbose=True)
    
    # Add tasks
    controller.add_task(example_task_for_multiprocessing, "A", 5)
    controller.add_task(example_task_for_multiprocessing, "B", 10)
    controller.add_task(example_task_for_multiprocessing, "C", 15)

    # Run all tasks
    controller.run_tasks()
    
    # Monitor tasks
    controller.monitor_tasks()

    # Optionally terminate tasks if needed
    controller.terminate_tasks()
    
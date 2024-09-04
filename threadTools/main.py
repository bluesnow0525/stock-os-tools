import logging
from examples import example_asyncio, example_multiprocessing, example_threading, example_request_limiter, example_request_queue_manager

if __name__ == "__main__":
    # Example usage of different modules
    logging.info("Running Asyncio Example")
    example_asyncio.main_asyncio()

    logging.info("Running Multiprocessing Example")
    example_multiprocessing.main()

    logging.info("Running Threading Example")
    example_threading.main()

    logging.info("Running RequestLimiter Example")
    example_request_limiter.main()

    logging.info("Running RequestQueueManager Example")
    example_request_queue_manager.main()

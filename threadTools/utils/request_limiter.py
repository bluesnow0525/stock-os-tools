import asyncio
import aiohttp
import requests
import time
import threading
import queue
import logging

class RequestLimiter:
    def __init__(self, max_requests_per_minute: int = 20, verbose: bool = False):
        """_summary_

        Args:
            max_requests_per_minute (int, optional): Use to setup requests per minute. Defaults to 20. Recommend to be lower than 20.
            verbose (bool, optional): Use to decide whether to show info or not. Defaults to True.
        """
        self.request_count = 0
        self.last_request_time = 0
        self.request_queue = queue.Queue()
        self.lock = threading.Lock()
        self.max_requests_per_minute = max_requests_per_minute
        self.verbose = verbose
        
        # Start the thread to monitor requests
        threading.Thread(target=self.monitor_requests, daemon=True).start()
    
    def log(self, message: str, level=logging.INFO):
        if self.verbose:
            logging.log(level, message)
    
    def make_request(self, url: str) -> None:
        """Add a new request URL to the queue."""
        self.request_queue.put(url)
        self.log(f'Added URL to queue: {url}')
    
    def monitor_requests(self) -> None:
        """Monitor and process the requests from the queue."""
        while True:
            current_time = time.time()
            
            with self.lock:
                # Reset request count if more than a minute has passed since the last request
                if current_time - self.last_request_time > 60:
                    self.request_count = 0
            
            # If the request limit is reached, wait before processing more requests
            if self.request_count >= self.max_requests_per_minute:
                time.sleep(1)
                continue
            
            try:
                # Get the next URL from the queue
                url = self.request_queue.get(timeout=1)
            except queue.Empty:
                time.sleep(1)
                continue
            
            response = requests.get(url)
            
            with self.lock:
                if response.status_code == 200:
                    self.request_count += 1
                    self.last_request_time = current_time
                    self.log(f'Successfully fetched URL: {url}')
                else:
                    # Re-add the URL to the queue if the request failed
                    self.request_queue.put(url)
                    self.log(f'Failed to fetch URL, re-added to queue: {url}', level=logging.WARNING)
            
            time.sleep(60/self.max_requests_per_minute)  # Simulate interval between requests
            
class AsyncioRequestLimiter:
    def __init__(self, max_requests_per_minute: int = 20, verbose: bool = False):
        """
        Initialize the RequestLimiter with a maximum number of requests per minute and verbosity.

        Args:
            max_requests_per_minute (int, optional): Maximum number of requests per minute. Defaults to 20.
            verbose (bool, optional): If True, log detailed information. Defaults to False.
        """
        self.request_count = 0
        self.last_request_time = 0
        self.request_queue = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.max_requests_per_minute = max_requests_per_minute
        self.verbose = verbose
        
        # Start the task to monitor requests
        asyncio.create_task(self.monitor_requests())
    
    def log(self, message: str, level=logging.INFO):
        if self.verbose:
            logging.log(level, message)
    
    async def make_request(self, url: str) -> None:
        """Add a new request URL to the queue."""
        await self.request_queue.put(url)
        self.log(f'Added URL to queue: {url}')
    
    async def monitor_requests(self) -> None:
        """Monitor and process the requests from the queue."""
        while True:
            current_time = time.time()
            
            async with self.lock:
                # Reset request count if more than a minute has passed since the last request
                if current_time - self.last_request_time > 60:
                    self.request_count = 0
            
            # If the request limit is reached, wait before processing more requests
            if self.request_count >= self.max_requests_per_minute:
                await asyncio.sleep(1)
                continue
            
            try:
                # Get the next URL from the queue
                url = await asyncio.wait_for(self.request_queue.get(), timeout=1)
            except asyncio.TimeoutError:
                await asyncio.sleep(1)
                continue
            
            async with self.lock:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            self.request_count += 1
                            self.last_request_time = current_time
                            self.log(f'Successfully fetched URL: {url}')
                        else:
                            # Re-add the URL to the queue if the request failed
                            await self.request_queue.put(url)
                            self.log(f'Failed to fetch URL, re-added to queue: {url}', level=logging.WARNING)
            
            await asyncio.sleep(60 / self.max_requests_per_minute)  # Simulate interval between requests
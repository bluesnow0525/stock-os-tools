import logging
from utils.request_limiter import RequestLimiter, AsyncioRequestLimiter
import time
import asyncio

def main():
    # Example usage of RequestLimiter
    limiter = RequestLimiter(max_requests_per_minute=10)  # Set custom rate limit
    
    # Add some example URLs to the request queue
    for i in range(30):
        limiter.make_request(f"https://httpbin.org/get?query={i}")
        logging.info(f'Pending {i + 1} request(s)')
    
    # Allow some time for the requests to be processed
    time.sleep(180)  # Wait for 3 minutes to ensure all requests are processed
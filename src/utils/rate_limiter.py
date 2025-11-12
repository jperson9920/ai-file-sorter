"""Rate limiter for API requests."""

import asyncio
from collections import deque
from datetime import datetime, timedelta


class RateLimiter:
    """Rate limiter for API requests using sliding window algorithm."""

    def __init__(self, requests_per_30s: int = 6):
        """Initialize rate limiter.

        Args:
            requests_per_30s: Maximum number of requests allowed per 30 seconds
        """
        self.max_requests = requests_per_30s
        self.window = timedelta(seconds=30)
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        async with self.lock:
            now = datetime.now()

            # Remove requests outside the sliding window
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()

            # Wait if at limit
            if len(self.requests) >= self.max_requests:
                sleep_time = (self.requests[0] + self.window - now).total_seconds()
                if sleep_time > 0:
                    # Add small buffer to ensure we don't hit limit
                    await asyncio.sleep(sleep_time + 0.1)

                    # Clean up again after waiting
                    now = datetime.now()
                    while self.requests and now - self.requests[0] > self.window:
                        self.requests.popleft()

            # Record this request
            self.requests.append(datetime.now())

    def get_stats(self) -> dict:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with current request count and window info
        """
        now = datetime.now()
        # Clean up old requests
        while self.requests and now - self.requests[0] > self.window:
            self.requests.popleft()

        return {
            'current_requests': len(self.requests),
            'max_requests': self.max_requests,
            'window_seconds': self.window.total_seconds(),
            'can_make_request': len(self.requests) < self.max_requests
        }

    def reset(self):
        """Reset the rate limiter (clear all tracked requests)."""
        self.requests.clear()

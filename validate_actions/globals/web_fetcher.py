"""Web fetching utilities with caching and retry logic.

This module provides a robust HTTP client implementation specifically designed
for fetching GitHub Actions metadata and other web resources. It includes:

- Response caching to avoid redundant requests
- Configurable retry logic with exponential backoff
- Timeout handling for network operations
- Clean abstraction through the IWebFetcher interface

Typical usage:
    fetcher = WebFetcher(max_retries=3, request_timeout=10)
    response = fetcher.fetch('https://api.github.com/repos/actions/checkout')
    if response:
        data = response.json()
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Optional

import requests


class IWebFetcher(ABC):
    """Abstract interface for web fetching with caching capabilities.

    This interface defines the contract for HTTP clients used throughout
    the validate-actions tool.

    Examples:
        Basic usage pattern:

        >>> fetcher = SomeWebFetcherImplementation()
        >>> response = fetcher.fetch('https://example.com/api/data')
        >>> if response and response.status_code == 200:
        ...     data = response.json()

        Cache management:

        >>> fetcher.clear_cache()  # Clear all cached responses
    """

    @abstractmethod
    def fetch(self, url: str) -> Optional[requests.Response]:
        """Fetch a URL and return the HTTP response.

        Args:
            url: The URL to fetch. Should be a valid HTTP/HTTPS URL.

        Returns:
            The HTTP response object if successful, None if the request
            failed after all retries or encountered an unrecoverable error.
        """
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear all cached HTTP responses.

        This method removes all entries from the internal response cache,
        forcing subsequent fetch() calls to make fresh HTTP requests.
        Useful for testing or when you need to ensure fresh data.
        """
        pass


class WebFetcher(IWebFetcher):
    """Implementation of IWebFetcher with caching and retry logic.

    This implementation provides robust HTTP fetching with the following features:

    - **Response Caching**: Successful responses are cached in memory to avoid
      redundant network requests during a single validation run.
    - **Retry Logic**: Failed requests are retried with exponential backoff
      to handle transient network issues.
    - **Timeout Handling**: Configurable request timeouts prevent hanging
      on slow or unresponsive servers.
    - **Session Reuse**: Reuses HTTP connections for better performance
      when making multiple requests.

    This class is specifically designed for fetching GitHub Actions metadata
    and other external resources needed for workflow validation.
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        max_retries: int = 3,
        request_timeout: int = 1,
        retry_backoff_factor: float = 0.01,
        github_token: Optional[str] = None,
    ) -> None:
        """Initialize the WebFetcher with configurable retry and timeout settings.

        Args:
            session: Optional requests.Session to use. If None, a new session
                will be created. Useful for customizing headers, authentication,
                or other session-level configuration.
            max_retries: Maximum number of retry attempts for failed requests.
                Default is 3. Set to 0 to disable retries.
            request_timeout: Timeout in seconds for each HTTP request.
                Default is 10 seconds. Applies to both connection and read timeouts.
            retry_backoff_factor: Multiplier for exponential backoff between retries.
                Default is 1.5. Sleep time = backoff_factor ^ attempt_number.

        Note:
            The cache is initialized as empty and will be populated as requests
            are made. Cache entries persist for the lifetime of the WebFetcher instance.
        """
        self.cache: Dict[str, Optional[requests.Response]] = {}
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.retry_backoff_factor = retry_backoff_factor
        if github_token:
            self.session.headers.update({"Authorization": f"token {github_token}"})
        print()

    def fetch(self, url: str) -> Optional[requests.Response]:
        """Fetch a URL with caching, retries, and exponential backoff.

        This method implements a robust HTTP fetching strategy:

        1. **Cache Check**: First checks if the URL has been fetched before
           and returns the cached response if available.
        2. **HTTP Request**: Makes an HTTP GET request with the configured timeout.
        3. **Status Validation**: Raises an exception for HTTP error status codes
           (4xx, 5xx), which triggers the retry logic.
        4. **Retry Logic**: On failure, retries up to `max_retries` times with
           exponential backoff delays between attempts.
        5. **Cache Storage**: Successful responses are cached. Failed requests
           (after all retries) are cached as None to avoid repeated attempts.

        Args:
            url: The URL to fetch. Must be a valid HTTP or HTTPS URL.

        Returns:
            The HTTP response object if the request succeeded (status 2xx),
            or None if the request failed after all retries.

        Note:
            - Successful responses remain in cache until clear_cache() is called
            - Failed requests are also cached (as None) to avoid retry loops
            - The exponential backoff helps avoid overwhelming failing servers
        """

        if url in self.cache:
            return self.cache[url]

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.request_timeout)
                response.raise_for_status()
                self.cache[url] = response
                return response
            except (requests.RequestException, requests.Timeout):
                if attempt < self.max_retries:
                    sleep_time = self.retry_backoff_factor
                    time.sleep(sleep_time)

        # Cache the failure to avoid repeated attempts
        self.cache[url] = None
        return None

    def clear_cache(self) -> None:
        """Clear all cached HTTP responses."""
        self.cache.clear()

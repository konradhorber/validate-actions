"""WebFetcher module for GitHub API interaction."""
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional

import requests


class WebFetcher(ABC):
    """Abstract interface for web fetching.

    This interface defines the contract for HTTP clients used throughout
    the validate-actions tool.

    Examples:
        Basic usage pattern:

        >>> fetcher = SomeWebFetcherImplementation()
        >>> response = fetcher.fetch('https://example.com/api/data')
        >>> if response and response.status_code == 200:
        ...     data = response.json()
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


class CachedWebFetcher(WebFetcher):
    """Implementation of WebFetcher with caching and retry logic.

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

    def fetch(self, url: str) -> Optional[requests.Response]:
        """Fetch a URL with caching and intelligent retry logic.

        This method implements a robust HTTP fetching strategy:

        1. **Cache Check**: First checks if the URL has been fetched before
           and returns the cached response if available.
        2. **HTTP Request**: Makes an HTTP GET request with the configured timeout.
        3. **Intelligent Retry Logic**: Only retries on errors that might be transient:
           - Network errors (timeouts, connection failures)
           - Server errors (5xx status codes)
           - Rate limiting (429 status code)
        4. **No Retry on Permanent Errors**: Client errors (4xx except 429) indicate
           permanent issues and are not retried.
        5. **Cache Storage**: Both successful and permanently failed requests are cached.

        Args:
            url: The URL to fetch. Must be a valid HTTP or HTTPS URL.

        Returns:
            The HTTP response object if the request succeeded (status 2xx),
            or None if the request failed permanently or after all retries.
        """

        if url in self.cache:
            return self.cache[url]

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.request_timeout)

                # Check for permanent client errors that shouldn't be retried
                if self._is_permanent_client_error(response.status_code):
                    self.cache[url] = None
                    return None

                response.raise_for_status()
                self.cache[url] = response
                return response

            except (requests.ConnectionError, requests.Timeout):
                # Network errors are retryable
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_factor)
            except requests.HTTPError:
                # HTTP errors (4xx, 5xx) are handled above via status code check
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_factor)
            except requests.RequestException:
                # Other request exceptions are not retried
                break

        # Cache the failure to avoid repeated attempts
        self.cache[url] = None
        return None

    def _is_permanent_client_error(self, status_code: int) -> bool:
        """Check if an HTTP status code represents a permanent client error.

        Permanent client errors should not be retried because they indicate
        problems with the request itself (wrong URL, missing auth, etc.) rather
        than transient network or server issues.

        Args:
            status_code: HTTP status code from the response

        Returns:
            True if this is a permanent client error that should not be retried
        """
        permanent_errors = {
            400,  # Bad Request - malformed request
            401,  # Unauthorized - missing/invalid auth
            403,  # Forbidden - insufficient permissions
            404,  # Not Found - resource doesn't exist
            405,  # Method Not Allowed - wrong HTTP method
            409,  # Conflict - state conflict
            410,  # Gone - resource permanently removed
            422,  # Unprocessable Entity - invalid request data
        }
        return status_code in permanent_errors

    def clear_cache(self) -> None:
        """Clear all cached HTTP responses."""
        self.cache.clear()

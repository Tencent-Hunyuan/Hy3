"""
06_error_handling.py — Hy3 Error Handling & Retry Example
==========================================================
Demo: Timeout handling + Rate limit retry + Network failure recovery + Exponential backoff

Run:
    python 06_error_handling.py

Environment Variables:
    HY3_BASE_URL  - API endpoint (default: http://127.0.0.1:8000/v1)
    HY3_API_KEY   - API key (default: EMPTY)
    HY3_MODEL     - Model name (default: hy3)
"""

import os
import time
import random
import logging
from typing import Optional
from openai import OpenAI, APIError, APITimeoutError, RateLimitError, APIConnectionError

# ── Logging configuration ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────
BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")


# ══════════════════════════════════════════════════════
# Utility: Request wrapper with retry
# ══════════════════════════════════════════════════════
def call_with_retry(
    client: OpenAI,
    messages: list,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    timeout: float = 120.0,
    **kwargs,
) -> dict:
    """
    API call wrapper with exponential backoff retry

    Strategy:
    - Network error (APIConnectionError): retry immediately
    - Timeout (APITimeoutError): retry with exponential backoff
    - Rate limit (RateLimitError): read Retry-After or exponential backoff
    - Other API errors: no retry, raise directly

    Args:
        client: OpenAI client
        messages: Conversation message list
        max_retries: Maximum retry attempts
        base_delay: Initial backoff delay (seconds)
        max_delay: Maximum backoff delay (seconds)
        timeout: Request timeout (seconds)
        **kwargs: Extra params for chat.completions.create

    Returns:
        API response object

    Raises:
        APIError: Non-retryable API error
        Exception: Max retries exceeded
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retrying (attempt {attempt}/{max_retries})")

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                timeout=timeout,
                **kwargs,
            )
            return response

        except RateLimitError as e:
            last_exception = e
            # Rate limit: prefer Retry-After header
            retry_after = getattr(e, "retry_after", None)
            if retry_after:
                delay = float(retry_after)
            else:
                delay = min(base_delay * (2 ** attempt), max_delay)
                # Add jitter to avoid thundering herd
                delay += random.uniform(0, delay * 0.1)

            logger.warning(
                f"Rate limit (429). "
                f"Waiting {delay:.1f}s before retry..."
            )
            time.sleep(delay)

        except APITimeoutError as e:
            last_exception = e
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay += random.uniform(0, delay * 0.1)
            logger.warning(
                f"Request timeout ({timeout}s). "
                f"Waiting {delay:.1f}s before retry..."
            )
            time.sleep(delay)

        except APIConnectionError as e:
            last_exception = e
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"Network connection failed: {e}. "
                f"Waiting {delay:.1f}s before retry..."
            )
            time.sleep(delay)

        except APIError as e:
            # Non-retryable errors (400, 401, 403, etc.)
            logger.error(f"API error (non-retryable): {e.status_code} - {e.message}")
            raise

    raise Exception(
        f"Max retries exceeded ({max_retries}). Last error: {last_exception}"
    )


# ══════════════════════════════════════════════════════
# Example 1: Basic retry usage
# ══════════════════════════════════════════════════════
def basic_retry_example():
    """Use the packaged retry function"""
    print("=" * 60)
    print("Example 1: Basic Retry Wrapper")
    print("=" * 60)

    # Create client with custom timeout
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=120.0,
    )

    messages = [
        {"role": "user", "content": "Hello, please introduce yourself."}
    ]

    try:
        response = call_with_retry(
            client,
            messages,
            max_retries=3,
            base_delay=1.0,
            temperature=0.9,
            max_tokens=256,
        )
        print(f"\n[Assistant]: {response.choices[0].message.content}")
        print(f"Tokens: {response.usage.total_tokens}")
    except Exception as e:
        print(f"\nRequest ultimately failed: {e}")


# ══════════════════════════════════════════════════════
# Example 2: Granular error classification
# ══════════════════════════════════════════════════════
def granular_error_handling():
    """Apply different strategies for different error types"""
    print("\n" + "=" * 60)
    print("Example 2: Granular Error Handling")
    print("=" * 60)

    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=30.0,  # Shorter timeout for demo purposes
    )

    messages = [
        {"role": "user", "content": "Explain what deep learning is."}
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
            max_tokens=512,
        )
        print(f"\n[Assistant]: {response.choices[0].message.content[:200]}...")

    except APITimeoutError:
        print("\nStrategy: Request timeout")
        print("  → Suggestion: Increase timeout parameter, or reduce max_tokens")
        print("  → Fallback: Return cached previous response (if available)")

    except RateLimitError as e:
        print("\nStrategy: Rate limit")
        print(f"  → Retry-After: {getattr(e, 'retry_after', 'N/A')}")
        print("  → Suggestion: Implement request queue, smooth request rate")
        print("  → Fallback: Downgrade to smaller model or return predefined response")

    except APIConnectionError:
        print("\nStrategy: Network failure")
        print("  → Suggestion: Check network connection and server status")
        print("  → Fallback: Switch to backup API endpoint (if available)")

    except APIError as e:
        print(f"\nStrategy: API error ({e.status_code})")
        if e.status_code == 400:
            print("  → Cause: Invalid request parameters")
            print("  → Suggestion: Check messages format and parameter ranges")
        elif e.status_code == 401:
            print("  → Cause: Authentication failed")
            print("  → Suggestion: Check if API Key is correct")
        elif e.status_code == 404:
            print("  → Cause: Model not found")
            print("  → Suggestion: Check if model parameter is correct")
        else:
            print(f"  → Cause: {e.message}")
            print("  → Suggestion: Check server logs")


# ══════════════════════════════════════════════════════
# Example 3: Production-grade request manager
# ══════════════════════════════════════════════════════
class Hy3RequestManager:
    """
    Production-grade request manager

    Features:
    - Auto retry with exponential backoff
    - Request rate control
    - Response caching (optional)
    - Health check
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        api_key: str = API_KEY,
        max_retries: int = 3,
        requests_per_minute: int = 60,
        timeout: float = 120.0,
    ):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        self.max_retries = max_retries
        self.rpm = requests_per_minute
        self.request_times: list = []
        self.timeout = timeout
        self._cache: dict = {}

    def _rate_limit(self):
        """Simple rate limiter: sliding window"""
        now = time.time()
        # Clean up records older than 60 seconds
        self.request_times = [t for t in self.request_times if now - t < 60]

        if len(self.request_times) >= self.rpm:
            wait_time = 60 - (now - self.request_times[0])
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                time.sleep(wait_time)

        self.request_times.append(time.time())

    def chat(
        self,
        messages: list,
        use_cache: bool = False,
        **kwargs,
    ) -> Optional[str]:
        """
        Send chat request

        Args:
            messages: Conversation messages
            use_cache: Whether to enable caching
            **kwargs: Extra params passed to API

        Returns:
            Assistant reply content, None on failure
        """
        # Cache key
        cache_key = str(messages) + str(kwargs)
        if use_cache and cache_key in self._cache:
            logger.info("Cache hit, returning cached result")
            return self._cache[cache_key]

        # Rate limiting
        self._rate_limit()

        # Request with retry
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    timeout=self.timeout,
                    **kwargs,
                )
                content = response.choices[0].message.content
                if use_cache:
                    self._cache[cache_key] = content
                return content

            except (APITimeoutError, APIConnectionError, RateLimitError) as e:
                delay = min(1.0 * (2 ** attempt), 30.0)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}): {type(e).__name__}. "
                    f"Waiting {delay:.1f}s..."
                )
                time.sleep(delay)

            except APIError as e:
                logger.error(f"Non-retryable error: {e.status_code} - {e.message}")
                return None

        logger.error(f"All {self.max_retries} retries failed")
        return None

    def health_check(self) -> bool:
        """Check if API service is available"""
        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                timeout=10.0,
            )
            return True
        except Exception:
            return False


def production_manager_example():
    """Use production-grade request manager"""
    print("\n" + "=" * 60)
    print("Example 3: Production Request Manager")
    print("=" * 60)

    manager = Hy3RequestManager(
        max_retries=3,
        requests_per_minute=30,
        timeout=60.0,
    )

    # Health check
    print("\n>>> Health check...")
    is_healthy = manager.health_check()
    print(f"    Service status: {'OK' if is_healthy else 'Unavailable'}")

    # Normal request
    print("\n>>> Sending normal request...")
    result = manager.chat(
        [{"role": "user", "content": "What is microservice architecture?"}],
        temperature=0.9,
        max_tokens=256,
    )
    if result:
        print(f"    Reply: {result[:200]}...")
    else:
        print("    Request failed")

    # Cached request
    print("\n>>> Sending cached request (same content 2nd time)...")
    messages = [{"role": "user", "content": "What does HTTP status code 200 mean?"}]
    result1 = manager.chat(messages, use_cache=True, max_tokens=64)
    result2 = manager.chat(messages, use_cache=True, max_tokens=64)  # Cache hit
    print(f"    1st: {result1}")
    print(f"    2nd: {result2} (cached)")


# ══════════════════════════════════════════════════════
# Example 4: Exponential backoff visualization
# ══════════════════════════════════════════════════════
def backoff_visualization():
    """Visualize the time distribution of exponential backoff strategy"""
    print("\n" + "=" * 60)
    print("Example 4: Exponential Backoff Visualization")
    print("=" * 60)

    base_delay = 1.0
    max_delay = 60.0
    max_retries = 5

    print(f"\nParams: base_delay={base_delay}s, max_delay={max_delay}s, max_retries={max_retries}")
    print(f"\n{'Retry':<12} {'Backoff(s)':<14} {'Cumulative(s)':<16} {'Timeline'}")
    print("-" * 70)

    cumulative = 0
    for attempt in range(max_retries + 1):
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, delay * 0.1)
        actual_delay = delay + jitter
        cumulative += actual_delay if attempt > 0 else 0

        # Visualize timeline
        bar_len = int(actual_delay * 2)  # 1 char per 0.5s
        bar = "█" * min(bar_len, 40)

        label = "Initial" if attempt == 0 else f"Retry #{attempt}"
        print(f"{label:<12} {actual_delay:<14.2f} {cumulative:<16.2f} {bar}")

    print(f"\nNotes:")
    print(f"• Wait time doubles each retry (exponential growth)")
    print(f"• Random jitter (±10%) to avoid thundering herd")
    print(f"• Max wait time capped at {max_delay}s")
    print(f"• Total wait cap for {max_retries} retries ≈ {cumulative:.1f}s")


# ── Main entry ───────────────────────────────────────────
if __name__ == "__main__":
    print("Hy3 Error Handling & Retry Example")
    print(f"API: {BASE_URL} | Model: {MODEL}\n")

    basic_retry_example()
    granular_error_handling()
    production_manager_example()
    backoff_visualization()

    print("\n" + "=" * 60)
    print("All error handling examples completed!")
    print("=" * 60)

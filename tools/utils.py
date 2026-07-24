"""Shared utility functions."""

from __future__ import annotations

import logging
import time
import urllib.error
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_on_rate_limit(
    fn: Callable[[], T],
    *,
    max_retries: int = 10,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """Call fn with exponential backoff on HTTP 429 responses."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == max_retries:
                raise
            logger.warning(
                "Rate limited (429), retrying in %.1fs (attempt %d/%d)",
                delay,
                attempt + 1,
                max_retries,
            )
            sleep_fn(delay)
            delay *= backoff_factor
    raise RuntimeError("retry_on_rate_limit: unreachable")

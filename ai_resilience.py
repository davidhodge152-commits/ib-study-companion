"""AI Resilience Layer — Retry, Circuit Breaker, Cache, Cost Tracking.

Provides a unified resilient_llm_call() entry point that wraps all LLM API
calls with retry logic, circuit breaking, response caching, and cost tracking.
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# ── TTL Cache ───────────────────────────────────────────────

class TTLCache:
    """In-memory dict with expiry timestamps and LRU eviction at 1000 entries."""

    MAX_ENTRIES = 1000

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}  # key -> (value, expires_at)
        self._lock = threading.Lock()

    @staticmethod
    def _make_key(prompt: str, system: str, model: str) -> str:
        raw = f"{prompt}|{system}|{model}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: str, ttl_seconds: int = 86400) -> None:
        with self._lock:
            if len(self._store) >= self.MAX_ENTRIES:
                self._evict_oldest()
            self._store[key] = (value, time.time() + ttl_seconds)

    def _evict_oldest(self) -> None:
        """Remove the entry with the earliest expiry."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k][1])
        del self._store[oldest_key]

    def cleanup(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]
            return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# ── Circuit Breaker ─────────────────────────────────────────

@dataclass
class _ProviderState:
    failures: int = 0
    state: str = "closed"  # closed | open | half_open
    last_failure_time: float = 0.0


class CircuitBreaker:
    """Per-provider state machine: closed -> open -> half_open -> closed."""

    FAILURE_THRESHOLD = 3
    RECOVERY_TIMEOUT = 60  # seconds

    def __init__(self) -> None:
        self._providers: dict[str, _ProviderState] = {}
        self._lock = threading.Lock()

    def _get_state(self, provider: str) -> _ProviderState:
        if provider not in self._providers:
            self._providers[provider] = _ProviderState()
        return self._providers[provider]

    def record_success(self, provider: str) -> None:
        with self._lock:
            state = self._get_state(provider)
            state.failures = 0
            state.state = "closed"

    def record_failure(self, provider: str) -> None:
        with self._lock:
            state = self._get_state(provider)
            state.failures += 1
            state.last_failure_time = time.time()
            if state.failures >= self.FAILURE_THRESHOLD:
                state.state = "open"

    def is_open(self, provider: str) -> bool:
        with self._lock:
            state = self._get_state(provider)
            if state.state == "closed":
                return False
            if state.state == "open":
                elapsed = time.time() - state.last_failure_time
                if elapsed >= self.RECOVERY_TIMEOUT:
                    state.state = "half_open"
                    return False  # allow one attempt
                return True
            # half_open — allow attempt
            return False

    def get_state(self, provider: str) -> str:
        with self._lock:
            return self._get_state(provider).state


# Module-level singletons
_circuit_breaker = CircuitBreaker()
_cache: TTLCache | None = None


def _get_cache() -> TTLCache:
    """Lazy-init the module-level TTLCache."""
    global _cache
    if _cache is None:
        _cache = TTLCache()
    return _cache


# ── Cost Tracker ────────────────────────────────────────────

# Approximate pricing per 1M tokens (input + output averaged)
_MODEL_PRICING: dict[str, float] = {
    "gemini-2.0-flash": 0.075,
    "gemini-1.5-flash": 0.075,
    "claude-sonnet-4-5-20250929": 3.0,
    "claude-sonnet-4-20250514": 3.0,
    "gpt-4o": 2.5,
    "gpt-4o-mini": 0.15,
}


class CostTracker:
    """Estimates tokens from character count and applies model-specific pricing."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate: 1 token ~ 4 characters."""
        return max(1, len(text) // 4)

    @staticmethod
    def track_call(
        model: str,
        input_text: str,
        output_text: str,
        latency_ms: int,
    ) -> dict:
        input_tokens = CostTracker.estimate_tokens(input_text)
        output_tokens = CostTracker.estimate_tokens(output_text)
        total_tokens = input_tokens + output_tokens

        price_per_million = _MODEL_PRICING.get(model, 1.0)
        cost_usd = (total_tokens / 1_000_000) * price_per_million

        return {
            "input_tokens_est": input_tokens,
            "output_tokens_est": output_tokens,
            "total_tokens_est": total_tokens,
            "cost_estimate_usd": round(cost_usd, 6),
            "model": model,
            "latency_ms": latency_ms,
        }


# ── Prompt Variant Selector ─────────────────────────────────

class PromptVariantSelector:
    """Deterministic A/B testing via user_id % len(variants)."""

    def __init__(self) -> None:
        self._experiments: dict[str, list[tuple[str, str]]] = {}

    def register(self, experiment: str, variants: list[tuple[str, str]]) -> None:
        """Register an experiment with named variants.

        Args:
            experiment: Name of the experiment.
            variants: List of (variant_name, prompt_text) tuples.
        """
        if not variants:
            raise ValueError("At least one variant required")
        self._experiments[experiment] = variants

    def select(self, experiment: str, user_id: int) -> tuple[str, str]:
        """Select a variant for a user.

        Returns:
            (variant_name, prompt_text) tuple.
        """
        variants = self._experiments.get(experiment)
        if not variants:
            return ("default", "")
        idx = user_id % len(variants)
        return variants[idx]


# ── Transient error detection ───────────────────────────────

_TRANSIENT_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def _is_transient(exc: BaseException) -> bool:
    """Check if an exception is transient (worth retrying)."""
    if isinstance(exc, _TRANSIENT_ERRORS):
        return True
    msg = str(exc).lower()
    transient_patterns = [
        "rate limit",
        "429",
        "503",
        "502",
        "500",
        "overloaded",
        "temporarily unavailable",
        "timeout",
        "connection",
    ]
    return any(p in msg for p in transient_patterns)


class TransientLLMError(Exception):
    """Wrapper for transient LLM errors that should be retried."""
    pass


# ── Main entry point ────────────────────────────────────────

def _do_call(provider: str, model: str, prompt: str, system: str, messages: list[dict] | None) -> str:
    """Execute the actual LLM API call (no retry, no cache)."""
    if provider == "gemini":
        import google.generativeai as genai
        import os
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
        m = genai.GenerativeModel(model)
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = m.generate_content(full_prompt)
        return response.text

    elif provider == "claude":
        import anthropic
        import os
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        msgs = messages or [{"role": "user", "content": prompt}]
        kwargs: dict = {"model": model, "max_tokens": 4096, "messages": msgs}
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text

    elif provider == "openai":
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        oai_messages: list[dict] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        if messages:
            oai_messages.extend(messages)
        else:
            oai_messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=model,
            messages=oai_messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    else:
        raise ValueError(f"Unknown provider: {provider}")


@retry(
    retry=retry_if_exception_type(TransientLLMError),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _call_with_retry(provider: str, model: str, prompt: str, system: str, messages: list[dict] | None) -> str:
    """Call LLM with tenacity retry on transient errors."""
    try:
        return _do_call(provider, model, prompt, system, messages)
    except Exception as exc:
        if _is_transient(exc):
            raise TransientLLMError(str(exc)) from exc
        raise


def resilient_llm_call(
    provider: str,
    model: str,
    prompt: str,
    system: str = "",
    messages: list[dict] | None = None,
    cache_ttl: int = 0,
) -> tuple[str, dict]:
    """Main entry point for resilient LLM calls.

    Args:
        provider: 'gemini', 'claude', or 'openai'
        model: Model name string
        prompt: The prompt text
        system: System prompt (optional)
        messages: Chat messages for multi-turn (optional)
        cache_ttl: Cache TTL in seconds (0 = no caching)

    Returns:
        (response_text, metadata_dict) where metadata includes tokens, cost,
        latency, cache_hit, provider, model.
    """
    # Check circuit breaker
    if _circuit_breaker.is_open(provider):
        raise RuntimeError(f"Circuit breaker open for provider: {provider}")

    # Check cache (prefer cache_backend if available, fall back to local TTLCache)
    try:
        from cache_backend import get_cache as _get_cache_backend
        cache = _get_cache_backend()
    except ImportError:
        cache = None

    cache_key = TTLCache._make_key(prompt, system, model)
    if cache_ttl > 0:
        cached = cache.get(cache_key) if cache else _get_cache().get(cache_key)
        if cached is not None:
            return cached, {
                "cache_hit": True,
                "provider": provider,
                "model": model,
                "input_tokens_est": 0,
                "output_tokens_est": 0,
                "cost_estimate_usd": 0.0,
                "latency_ms": 0,
            }

    # Call with retry
    start = time.time()
    try:
        response_text = _call_with_retry(provider, model, prompt, system, messages)
    except Exception as exc:
        _circuit_breaker.record_failure(provider)
        raise

    latency_ms = int((time.time() - start) * 1000)
    _circuit_breaker.record_success(provider)

    # Cache the result
    if cache_ttl > 0:
        if cache:
            cache.set(cache_key, response_text, cache_ttl)
        else:
            _get_cache().set(cache_key, response_text, cache_ttl)

    # Track cost
    input_text = system + prompt + (str(messages) if messages else "")
    metrics = CostTracker.track_call(model, input_text, response_text, latency_ms)
    metrics["cache_hit"] = False
    metrics["provider"] = provider

    return response_text, metrics


def get_circuit_breaker() -> CircuitBreaker:
    """Access the module-level circuit breaker singleton."""
    return _circuit_breaker


def get_cache() -> TTLCache:
    """Access the module-level TTLCache singleton."""
    return _get_cache()

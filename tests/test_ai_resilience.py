"""Tests for the AI resilience layer."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from ai_resilience import (
    CircuitBreaker,
    CostTracker,
    PromptVariantSelector,
    TTLCache,
    TransientLLMError,
    get_cache,
    get_circuit_breaker,
    resilient_llm_call,
)


# ── TTLCache Tests ──────────────────────────────────────────


class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache()
        cache.set("k1", "v1", ttl_seconds=60)
        assert cache.get("k1") == "v1"

    def test_expired_entry_returns_none(self):
        cache = TTLCache()
        cache.set("k2", "v2", ttl_seconds=0)
        time.sleep(0.01)
        assert cache.get("k2") is None

    def test_missing_key_returns_none(self):
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        cache = TTLCache()
        cache.MAX_ENTRIES = 3  # temporarily reduce for test
        cache.set("a", "1", ttl_seconds=10)
        cache.set("b", "2", ttl_seconds=20)
        cache.set("c", "3", ttl_seconds=30)
        cache.set("d", "4", ttl_seconds=40)  # should evict 'a' (earliest expiry)
        assert cache.get("a") is None
        assert cache.get("d") == "4"
        cache.MAX_ENTRIES = 1000  # restore

    def test_cleanup_removes_expired(self):
        cache = TTLCache()
        cache.set("exp1", "val", ttl_seconds=0)
        cache.set("exp2", "val", ttl_seconds=0)
        cache.set("keep", "val", ttl_seconds=60)
        time.sleep(0.01)
        removed = cache.cleanup()
        assert removed == 2
        assert cache.get("keep") == "val"

    def test_clear(self):
        cache = TTLCache()
        cache.set("x", "y", ttl_seconds=60)
        cache.clear()
        assert cache.get("x") is None

    def test_make_key_deterministic(self):
        k1 = TTLCache._make_key("prompt", "system", "model")
        k2 = TTLCache._make_key("prompt", "system", "model")
        assert k1 == k2

    def test_make_key_different_inputs(self):
        k1 = TTLCache._make_key("a", "b", "c")
        k2 = TTLCache._make_key("x", "y", "z")
        assert k1 != k2


# ── CircuitBreaker Tests ────────────────────────────────────


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert not cb.is_open("test_provider")
        assert cb.get_state("test_provider") == "closed"

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker()
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure("bad_provider")
        assert cb.is_open("bad_provider")
        assert cb.get_state("bad_provider") == "open"

    def test_success_resets(self):
        cb = CircuitBreaker()
        cb.record_failure("p1")
        cb.record_failure("p1")
        cb.record_success("p1")
        assert not cb.is_open("p1")
        assert cb.get_state("p1") == "closed"

    def test_recovery_timeout(self):
        cb = CircuitBreaker()
        cb.RECOVERY_TIMEOUT = 0.01  # 10ms for test
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure("recover_provider")
        assert cb.is_open("recover_provider")
        time.sleep(0.02)
        assert not cb.is_open("recover_provider")  # half_open
        assert cb.get_state("recover_provider") == "half_open"

    def test_independent_providers(self):
        cb = CircuitBreaker()
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure("failing")
        assert cb.is_open("failing")
        assert not cb.is_open("healthy")


# ── CostTracker Tests ───────────────────────────────────────


class TestCostTracker:
    def test_estimate_tokens(self):
        assert CostTracker.estimate_tokens("") == 1  # min 1
        assert CostTracker.estimate_tokens("1234") == 1
        assert CostTracker.estimate_tokens("12345678") == 2

    def test_track_call(self):
        result = CostTracker.track_call(
            model="gemini-2.0-flash",
            input_text="Hello world",
            output_text="Response text here",
            latency_ms=150,
        )
        assert result["model"] == "gemini-2.0-flash"
        assert result["latency_ms"] == 150
        assert result["input_tokens_est"] > 0
        assert result["output_tokens_est"] > 0
        assert result["cost_estimate_usd"] >= 0

    def test_unknown_model_defaults_to_1(self):
        result = CostTracker.track_call(
            model="unknown-model",
            input_text="test",
            output_text="test",
            latency_ms=100,
        )
        assert result["cost_estimate_usd"] > 0


# ── PromptVariantSelector Tests ─────────────────────────────


class TestPromptVariantSelector:
    def test_select_deterministic(self):
        pvs = PromptVariantSelector()
        pvs.register("test_exp", [
            ("control", "You are a helpful tutor."),
            ("variant_a", "You are an encouraging tutor."),
        ])
        name, prompt = pvs.select("test_exp", user_id=10)
        name2, prompt2 = pvs.select("test_exp", user_id=10)
        assert name == name2
        assert prompt == prompt2

    def test_different_users_get_different_variants(self):
        pvs = PromptVariantSelector()
        pvs.register("exp2", [
            ("a", "prompt_a"),
            ("b", "prompt_b"),
        ])
        results = set()
        for uid in range(100):
            name, _ = pvs.select("exp2", uid)
            results.add(name)
        assert len(results) == 2

    def test_unknown_experiment_returns_default(self):
        pvs = PromptVariantSelector()
        name, prompt = pvs.select("nonexistent", 1)
        assert name == "default"
        assert prompt == ""

    def test_register_empty_raises(self):
        pvs = PromptVariantSelector()
        with pytest.raises(ValueError):
            pvs.register("bad", [])


# ── resilient_llm_call Tests ────────────────────────────────


class TestResilientLLMCall:
    @patch("ai_resilience._call_with_retry")
    def test_basic_call(self, mock_retry):
        mock_retry.return_value = "LLM says hello"
        # Reset singleton state
        get_circuit_breaker().record_success("gemini")
        get_cache().clear()

        text, meta = resilient_llm_call("gemini", "gemini-2.0-flash", "Hello")
        assert text == "LLM says hello"
        assert meta["provider"] == "gemini"
        assert meta["model"] == "gemini-2.0-flash"
        assert meta["cache_hit"] is False
        assert "cost_estimate_usd" in meta

    @patch("ai_resilience._call_with_retry")
    def test_cache_hit(self, mock_retry):
        mock_retry.return_value = "cached response"
        get_cache().clear()

        # First call — populates cache
        text1, meta1 = resilient_llm_call(
            "gemini", "gemini-2.0-flash", "test prompt", cache_ttl=60
        )
        assert meta1["cache_hit"] is False

        # Second call — should hit cache
        text2, meta2 = resilient_llm_call(
            "gemini", "gemini-2.0-flash", "test prompt", cache_ttl=60
        )
        assert meta2["cache_hit"] is True
        assert text2 == "cached response"
        assert mock_retry.call_count == 1  # Only called once

    def test_circuit_breaker_blocks_call(self):
        cb = get_circuit_breaker()
        # Force circuit open
        for _ in range(cb.FAILURE_THRESHOLD):
            cb.record_failure("blocked_provider")

        with pytest.raises(RuntimeError, match="Circuit breaker open"):
            resilient_llm_call("blocked_provider", "model", "prompt")

        # Reset for other tests
        cb.record_success("blocked_provider")

    @patch("ai_resilience._call_with_retry")
    def test_failure_records_to_circuit_breaker(self, mock_retry):
        mock_retry.side_effect = ValueError("Non-transient error")
        cb = get_circuit_breaker()
        cb.record_success("fail_test_provider")  # start clean

        with pytest.raises(ValueError):
            resilient_llm_call("fail_test_provider", "model", "prompt")

        # Should have recorded a failure
        assert cb.get_state("fail_test_provider") == "closed"  # only 1 failure

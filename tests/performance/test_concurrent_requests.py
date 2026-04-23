"""Performance tests for concurrent API request handling.

This module tests the async API implementation in ClaudeProvider.

ARCHITECTURAL NOTE — True async concurrency with aiobreaker
============================================================
ClaudeProvider.generate() uses aiobreaker's call_async() method to wrap
the circuit breaker call. Unlike pybreaker (which required asyncio.to_thread
and asyncio.run() workarounds), aiobreaker natively supports async/await.

The async API calls now execute concurrently within a single event loop,
so asyncio.gather() dispatches N coroutines that complete in roughly the
time of 1 request — achieving true wall-clock speedup (N concurrent requests
complete in ~1x latency instead of N x latency).

The tests below verify this concurrent execution behavior and measure the
actual speedup achieved.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest
from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from src.agent.providers.claude import ClaudeProvider
from src.common.types import ProviderRequest

# Simulated per-request API latency (seconds)
SIMULATED_LATENCY = 0.5


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client_with_latency() -> Mock:
    """Create a mock client that simulates realistic API latency."""
    mock_client = Mock(spec=AsyncAnthropic)

    async def mock_create(*args: object, **kwargs: object) -> Mock:
        await asyncio.sleep(SIMULATED_LATENCY)
        mock_text_block = TextBlock(text="Test answer", type="text")
        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        return mock_response

    mock_client.messages.create = AsyncMock(side_effect=mock_create)
    return mock_client


@pytest.fixture
def provider_with_latency(mock_client_with_latency: Mock) -> ClaudeProvider:
    """Create a provider with mocked latency for performance testing."""
    return ClaudeProvider(client=mock_client_with_latency, fail_max=5, reset_timeout=60)


def create_test_request(index: int) -> ProviderRequest:
    """Create a test ProviderRequest with a unique prompt per index."""
    return ProviderRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt=f"Test question number {index}",
        model_name="claude-3-5-sonnet-20241022",
    )


async def run_sequential(
    provider: ClaudeProvider, requests: list[ProviderRequest]
) -> tuple[list[tuple[str, int, int]], float]:
    """Run requests sequentially and return results with elapsed time."""
    start = time.perf_counter()
    results = []
    for req in requests:
        result = await provider.generate(req)
        results.append(result)
    elapsed = time.perf_counter() - start
    return results, elapsed


async def run_concurrent(
    provider: ClaudeProvider, requests: list[ProviderRequest]
) -> tuple[list[tuple[str, int, int]], float]:
    """Run requests via asyncio.gather and return results with elapsed time."""
    start = time.perf_counter()
    results = await asyncio.gather(*[provider.generate(req) for req in requests])
    elapsed = time.perf_counter() - start
    return list(results), elapsed


def _make_provider(fail_max: int = 20) -> ClaudeProvider:
    """Build a fresh ClaudeProvider with a latency-simulating mock client."""
    mock_client = Mock(spec=AsyncAnthropic)

    async def mock_create(*args: object, **kwargs: object) -> Mock:
        await asyncio.sleep(SIMULATED_LATENCY)
        mock_text_block = TextBlock(text="Test answer", type="text")
        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        return mock_response

    mock_client.messages.create = AsyncMock(side_effect=mock_create)
    return ClaudeProvider(client=mock_client, fail_max=fail_max, reset_timeout=60)


# ---------------------------------------------------------------------------
# Correctness tests — these must always pass
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_single_request_succeeds(provider_with_latency: ClaudeProvider) -> None:
    """Baseline: a single request completes successfully."""
    request = create_test_request(0)
    result = await provider_with_latency.generate(request)

    assert isinstance(result, tuple)
    assert len(result) == 3
    text, input_tokens, output_tokens = result
    assert text == "Test answer"
    assert input_tokens == 10
    assert output_tokens == 5


@pytest.mark.asyncio
async def test_5_concurrent_requests_all_succeed(provider_with_latency: ClaudeProvider) -> None:
    """5 concurrent requests all complete successfully."""
    n = 5
    requests = [create_test_request(i) for i in range(n)]
    results, elapsed = await run_concurrent(provider_with_latency, requests)

    assert len(results) == n
    for text, input_tokens, output_tokens in results:
        assert text == "Test answer"
        assert input_tokens == 10
        assert output_tokens == 5

    print(f"\n[5 concurrent] elapsed={elapsed:.3f}s")


@pytest.mark.asyncio
async def test_10_concurrent_requests_all_succeed(provider_with_latency: ClaudeProvider) -> None:
    """10 concurrent requests all complete successfully."""
    n = 10
    requests = [create_test_request(i) for i in range(n)]
    results, elapsed = await run_concurrent(provider_with_latency, requests)

    assert len(results) == n
    for text, input_tokens, output_tokens in results:
        assert text == "Test answer"

    print(f"\n[10 concurrent] elapsed={elapsed:.3f}s")


@pytest.mark.asyncio
async def test_no_race_conditions(provider_with_latency: ClaudeProvider) -> None:
    """Verify no race conditions: all concurrent results are independent and correct."""
    n = 10
    requests = [create_test_request(i) for i in range(n)]

    results = await asyncio.gather(*[provider_with_latency.generate(req) for req in requests])

    assert len(results) == n
    for i, result in enumerate(results):
        assert isinstance(result, tuple), f"Result {i} is not a tuple"
        assert len(result) == 3, f"Result {i} has wrong length"
        text, input_tokens, output_tokens = result
        assert isinstance(text, str), f"Result {i} text is not a string"
        assert isinstance(input_tokens, int), f"Result {i} input_tokens is not int"
        assert isinstance(output_tokens, int), f"Result {i} output_tokens is not int"


# ---------------------------------------------------------------------------
# Performance / concurrency characterisation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_execution_achieves_speedup() -> None:
    """Verify that asyncio.gather provides genuine wall-clock speedup.

    After migrating from pybreaker to aiobreaker, the circuit breaker now
    properly supports async execution. The async sleep (or real network I/O)
    no longer blocks threads, so N concurrent coroutines complete in roughly
    the time of 1 request — achieving true concurrency.

    This test verifies that concurrent execution is significantly faster than
    sequential execution (speedup >= 3x for 5 concurrent requests).
    """
    n = 5
    provider = _make_provider()

    requests = [create_test_request(i) for i in range(n)]
    seq_results, seq_time = await run_sequential(provider, requests)
    conc_results, conc_time = await run_concurrent(provider, requests)

    speedup = seq_time / conc_time

    print(f"\n[Concurrency characterisation n={n}]")
    print(f"  Sequential:  {seq_time:.3f}s")
    print(f"  Concurrent:  {conc_time:.3f}s")
    print(f"  Speedup:     {speedup:.2f}x  (expected ~{n}x with true async concurrency)")

    assert len(seq_results) == n
    assert len(conc_results) == n

    # Speedup should be close to n (5x) — confirming true concurrent execution.
    # Allow for some overhead, so require at least 3x speedup.
    assert speedup >= 3.0, (
        f"Insufficient speedup {speedup:.2f}x — expected at least 3x for {n} concurrent requests. "
        f"This suggests the async concurrency is not working correctly."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("n_requests", [1, 5, 10])
async def test_concurrency_levels_timing(n_requests: int) -> None:
    """Report timing for different concurrency levels (informational).

    With the current asyncio.run() architecture, elapsed time scales linearly
    with n_requests.  This test documents that behaviour and verifies the
    timing stays within the expected sequential bound (latency * n * 1.2).
    """
    provider = _make_provider()

    requests = [create_test_request(i) for i in range(n_requests)]
    results, elapsed = await run_concurrent(provider, requests)

    assert len(results) == n_requests

    # Upper bound: sequential worst-case with 20% overhead
    max_expected = SIMULATED_LATENCY * n_requests * 1.2
    assert elapsed < max_expected, (
        f"n={n_requests}: elapsed {elapsed:.3f}s exceeded sequential bound {max_expected:.3f}s"
    )

    print(f"\n[n={n_requests:2d}] elapsed={elapsed:.3f}s  (sequential bound={max_expected:.3f}s)")

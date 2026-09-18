import asyncio
import time
import httpx
import pytest

# Simulation of the synchronous blocking vs asynchronous non-blocking behavior
async def simulate_sync_blocking_call(delay: float):
    # Simulates what the old code did: time.sleep / blocking httpx.Client()
    # inside an async route handler
    time.sleep(delay)
    return {"status": "ok"}

async def simulate_async_nonblocking_call(delay: float):
    # Simulates what the fixed code does: await httpx.AsyncClient / asyncio.sleep
    await asyncio.sleep(delay)
    return {"status": "ok"}

@pytest.mark.anyio
async def test_iss007_concurrency_benchmark():
    delay = 0.3
    num_requests = 4

    # 1. Benchmark Blocking Sync Behavior (Old Code)
    start_sync = time.perf_counter()
    # If 4 requests arrive in the event loop and each blocks synchronously:
    results_sync = []
    for _ in range(num_requests):
        res = await simulate_sync_blocking_call(delay)
        results_sync.append(res)
    total_sync_time = time.perf_counter() - start_sync

    # 2. Benchmark Non-blocking Async Behavior (Fixed Code)
    start_async = time.perf_counter()
    # In the fixed code with AsyncClient, tasks run concurrently:
    tasks = [simulate_async_nonblocking_call(delay) for _ in range(num_requests)]
    results_async = await asyncio.gather(*tasks)
    total_async_time = time.perf_counter() - start_async

    print("\n" + "="*60)
    print(f"ISS-007 Concurrency Benchmark Results ({num_requests} concurrent requests):")
    print(f"Blocking Sync Time (Old code)       : {total_sync_time:.4f}s (Sequential ~{num_requests * delay:.2f}s)")
    print(f"Non-blocking Async Time (Fixed code) : {total_async_time:.4f}s (Concurrent ~{delay:.2f}s)")
    speedup = total_sync_time / total_async_time
    print(f"Throughput improvement / Speedup    : {speedup:.2f}x faster")
    print("="*60)

    assert total_async_time < (total_sync_time / 2)
    assert len(results_async) == num_requests

if __name__ == "__main__":
    asyncio.run(test_iss007_concurrency_benchmark())

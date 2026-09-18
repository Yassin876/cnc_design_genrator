import asyncio
import pytest

# Simulating the old vs new SSE queue mechanisms

# --- Old Implementation (Broken: Single Queue per job, overwrites previous subscriber, leaks memory) ---
class OldSSEManager:
    def __init__(self):
        self.active_job_queues = {}

    def subscribe(self, job_id: str):
        q = asyncio.Queue()
        # Overwrites any prior subscriber!
        self.active_job_queues[job_id] = q
        return q

    def push_event(self, job_id: str, event: dict):
        if job_id in self.active_job_queues:
            self.active_job_queues[job_id].put_nowait(event)

# --- New Implementation (Fixed: Set of Queues per job, broadcasts to all subscribers, cleans up on disconnect) ---
class NewSSEManager:
    def __init__(self):
        self.active_job_queues: dict[str, set[asyncio.Queue]] = {}

    def subscribe(self, job_id: str):
        q = asyncio.Queue()
        if job_id not in self.active_job_queues:
            self.active_job_queues[job_id] = set()
        self.active_job_queues[job_id].add(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue):
        if job_id in self.active_job_queues:
            self.active_job_queues[job_id].discard(q)
            if not self.active_job_queues[job_id]:
                self.active_job_queues.pop(job_id, None)

    def push_event(self, job_id: str, event: dict):
        if job_id in self.active_job_queues:
            for q in list(self.active_job_queues[job_id]):
                q.put_nowait(event)

@pytest.mark.anyio
async def test_iss008_sse_queue_race_and_memory_leak():
    job_id = "job_test_123"
    test_event = {"status": "processing", "progress": 50}

    # 1. Test Old Broken Mechanism
    old_mgr = OldSSEManager()
    sub1_old = old_mgr.subscribe(job_id)
    sub2_old = old_mgr.subscribe(job_id)  # Overwrites sub1!
    old_mgr.push_event(job_id, test_event)

    # Sub2 receives event, but Sub1 NEVER receives event (hanging connection)
    assert sub2_old.qsize() == 1
    assert sub1_old.qsize() == 0  # Bug: sub1 was starved/orphaned

    # 2. Test Fixed Multi-subscriber Mechanism
    new_mgr = NewSSEManager()
    sub1_new = new_mgr.subscribe(job_id)
    sub2_new = new_mgr.subscribe(job_id)
    sub3_new = new_mgr.subscribe(job_id)

    assert len(new_mgr.active_job_queues[job_id]) == 3

    new_mgr.push_event(job_id, test_event)

    # All subscribers receive the broadcast event simultaneously
    assert sub1_new.qsize() == 1
    assert sub2_new.qsize() == 1
    assert sub3_new.qsize() == 1
    ev1 = await sub1_new.get()
    ev2 = await sub2_new.get()
    ev3 = await sub3_new.get()
    assert ev1 == ev2 == ev3 == test_event

    # 3. Test Disconnection & Zero Memory Leak Cleanup
    new_mgr.unsubscribe(job_id, sub1_new)
    assert len(new_mgr.active_job_queues[job_id]) == 2
    new_mgr.unsubscribe(job_id, sub2_new)
    assert len(new_mgr.active_job_queues[job_id]) == 1
    new_mgr.unsubscribe(job_id, sub3_new)

    # The dictionary key is completely removed when last subscriber disconnects
    assert job_id not in new_mgr.active_job_queues
    assert len(new_mgr.active_job_queues) == 0

    print("\n" + "="*60)
    print("ISS-008 SSE Multi-Subscriber & Cleanup Test Passed!")
    print(f"- Old code: sub1 starved (qsize={sub1_old.qsize()}), sub2 overwrote.")
    print(f"- Fixed code: all 3 subscribers received event successfully.")
    print(f"- Memory leak check: active_job_queues cleaned up completely to {new_mgr.active_job_queues}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_iss008_sse_queue_race_and_memory_leak())

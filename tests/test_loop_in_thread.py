from __future__ import annotations

import threading
from concurrent.futures import Future

from bitcoin_safe_lib.async_tools.loop_in_thread import LoopInThread, MultipleStrategy


def test_run_background_does_not_deadlock_when_future_is_already_done(monkeypatch) -> None:
    loop_in_thread = LoopInThread()

    def immediate_schedule(coro):
        try:
            coro.close()
        except Exception:
            pass
        future: Future[None] = Future()
        future.set_result(None)
        return future

    monkeypatch.setattr(loop_in_thread, "_schedule", immediate_schedule)

    finished = threading.Event()

    def invoke_run_background() -> None:
        async def immediate() -> None:
            return None

        loop_in_thread.run_background(
            immediate(),
            key="already-done",
            multiple_strategy=MultipleStrategy.QUEUE,
        )
        finished.set()

    worker = threading.Thread(target=invoke_run_background)
    worker.start()
    worker.join(timeout=1)

    try:
        assert not worker.is_alive()
        assert finished.is_set()
    finally:
        loop_in_thread.stop()

#
# Bitcoin Safe
# Copyright (C) 2024 Andreas Griffin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see https://www.gnu.org/licenses/gpl-3.0.html
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import asyncio
import logging
import sys
import threading
from concurrent.futures import CancelledError, Future
from enum import Enum, auto
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    TypeVar,
)

from PyQt6.QtCore import QObject, Qt, pyqtSignal

logger = logging.getLogger(__name__)


class _GuiInvoker(QObject):
    """
    Queues function calls onto the Qt main thread via a signal/slot.
    """

    invoke = pyqtSignal(object, tuple)

    def __init__(self):
        super().__init__()
        # Always queued, even if emitted from main thread
        self.invoke.connect(self._dispatch, Qt.ConnectionType.QueuedConnection)

    @staticmethod
    def _dispatch(func, args):
        func(*args)


_GUI_INVOKER = _GuiInvoker()

_T = TypeVar("_T")
_OnSuccess = Callable[[Any], None]
_OnDone = Callable[[Any], None]
_OnError = Callable[[tuple], None]
_Cancel = Callable[[], None]


class MultipleStrategy(Enum):
    QUEUE = auto()
    REJECT_NEW_TASK = auto()
    CANCEL_OLD_TASK = auto()
    RUN_INDEPENDENT = auto()


class LoopInThread:
    """
    Runs an asyncio event loop in a daemon thread with optional key-based task strategies.

    Methods:
      - run_background: schedules a coroutine, returns concurrent.Future.
      - run_parallel: returns an asyncio.Future you can `await` from async code.
      - run_foreground: blocks until done.
      - run_task: callback style.
    """

    def __init__(
        self,
    ):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._tasks: Dict[Future[Any], _Cancel] = {}
        self._key_tasks: Dict[str, List[Future[Any]]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

        self._start()

    def _get_bucket(self, key: str):
        with self._global_lock:
            bucket = self._key_tasks.setdefault(key, [])
            lock = self._locks.setdefault(key, threading.Lock())
        return bucket, lock

    def _start(self):
        if self._loop:
            raise RuntimeError("LoopInThread already started")
        loop = asyncio.new_event_loop()

        def _runner():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=_runner, daemon=True, name="AsyncioLoopThread")
        thread.start()
        self._loop = loop
        self._thread = thread

    def _schedule(self, coro: Coroutine[Any, Any, _T]) -> Future[_T]:
        if not self._loop or not self._loop.is_running():
            logger.error("Loop is not running; cannot schedule task.")
            fut = Future()
            fut.set_running_or_notify_cancel()
            fut.cancel()
            return fut
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def run_background(
        self,
        coro: Coroutine[Any, Any, _T],
        key: Optional[str] = None,
        multiple_strategy: MultipleStrategy = MultipleStrategy.RUN_INDEPENDENT,
    ) -> Future[_T]:
        # No key logic: fire-and-forget on the loop
        if key is None or multiple_strategy is MultipleStrategy.RUN_INDEPENDENT:
            return self._schedule(coro)

        bucket, lock = self._get_bucket(key)
        cancel_list: List[Future[Any]] = []

        with lock:
            if multiple_strategy is MultipleStrategy.REJECT_NEW_TASK:
                if any(not f.done() for f in bucket):
                    fut = Future()
                    fut.set_running_or_notify_cancel()
                    fut.cancel()
                    return fut

            if multiple_strategy is MultipleStrategy.CANCEL_OLD_TASK and bucket:
                cancel_list = list(bucket)
                bucket.clear()

            if multiple_strategy is MultipleStrategy.QUEUE and bucket:
                parent = bucket[-1]

                async def wrapper() -> _T:
                    try:
                        await asyncio.wrap_future(parent)
                    except Exception:
                        pass
                    return await coro

                scheduled = wrapper()
            else:
                scheduled = coro

            fut = self._schedule(scheduled)
            bucket.append(fut)

            def cleanup(done: Future[Any], _bucket=bucket, _lock=lock):
                with _lock:
                    if done in _bucket:
                        _bucket.remove(done)
                    if not _bucket:
                        with self._global_lock:
                            self._key_tasks.pop(key, None)
                            self._locks.pop(key, None)

            fut.add_done_callback(cleanup)

        # cancel old tasks outside the lock to avoid deadlock
        for old in cancel_list:
            self.cancel_task(old)

        return fut

    def run_parallel(
        self,
        coros: Iterable[Coroutine[Any, Any, _T]],
        key: Optional[str] = None,
        multiple_strategy: MultipleStrategy = MultipleStrategy.RUN_INDEPENDENT,
    ) -> Awaitable[List[_T]]:
        """
        Schedule multiple coroutines under the same key/strategy.
        Returns an asyncio.Future you can `await` (it wraps the concurrent.Future).
        """
        # Schedule each on the loop (concurrent.Future)
        futures = [self.run_background(c, key=key, multiple_strategy=multiple_strategy) for c in coros]

        async def gather_all() -> List[_T]:
            async_futs = [asyncio.wrap_future(f) for f in futures]
            return await asyncio.gather(*async_futs)

        # Schedule gather_all on the loop and wrap for awaiting
        concurrent = self._schedule(gather_all())
        return asyncio.wrap_future(concurrent)

    async def gather(
        self,
        coroutines: Iterable[Coroutine[Any, Any, _T]],
        key: Optional[str] = None,
        multiple_strategy: MultipleStrategy = MultipleStrategy.RUN_INDEPENDENT,
        early_finish_criteria_function: Optional[Callable[[Sequence[_T]], bool]] = None,
    ) -> List[_T]:
        """Run *coros* on the background loop and return their results.

        Parameters
        ----------
        coros:
            The coroutines to execute on the background event loop.
        key / multiple_strategy:
            Forwarded to :meth:`run_background` to control key based execution
            behaviour.
        early_finish_criteria_function:
            An optional callback that receives the list of collected results so
            far.  If it returns ``True`` the remaining coroutines are cancelled
            and the gathered results are returned immediately.

        Example
        -------
        The method is particularly useful for "collect until enough" style
        workflows.

        Returns
        -------
        list
            The list of results produced by the completed coroutines.  When an
            early finish callback is provided the list only contains the results
            that completed before the callback returned ``True``.
        """

        if not coroutines:
            return []

        futures = [
            self.run_background(coro, key=key, multiple_strategy=multiple_strategy) for coro in coroutines
        ]

        async def _gather() -> List[_T]:
            async_futures = [asyncio.wrap_future(fut) for fut in futures]
            pending: set[asyncio.Future[_T]] = set(async_futures)
            results: List[_T] = []

            try:
                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                    for fut in done:
                        try:
                            result = fut.result()
                        except BaseException:
                            for remaining in pending:
                                remaining.cancel()
                            if pending:
                                await asyncio.gather(*pending, return_exceptions=True)
                            raise

                        results.append(result)

                    if early_finish_criteria_function and early_finish_criteria_function(results):
                        for remaining in pending:
                            remaining.cancel()
                        if pending:
                            await asyncio.gather(*pending, return_exceptions=True)
                        return results

                return results
            finally:
                if pending:
                    for fut in pending:
                        fut.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)

        return await asyncio.wrap_future(self._schedule(_gather()))

    def run_foreground(self, coro: Coroutine[Any, Any, _T]) -> _T:
        # Blocks calling thread until coro completes
        return self._schedule(coro).result()

    def run_task(
        self,
        coro: Coroutine[Any, Any, _T],
        on_success: Optional[_OnSuccess] = None,
        on_done: Optional[_OnDone] = None,
        on_error: Optional[_OnError] = None,
        cancel: Optional[_Cancel] = None,
        key: Optional[str] = None,
        multiple_strategy: MultipleStrategy = MultipleStrategy.RUN_INDEPENDENT,
    ) -> Future[_T]:
        fut = self.run_background(coro, key=key, multiple_strategy=multiple_strategy)
        if cancel:
            self._tasks[fut] = cancel

        def _handle(f: Future[_T]):
            result = None  # ensure defined
            if f.cancelled():
                pass
            else:
                try:
                    result = f.result()
                except CancelledError:
                    pass
                except Exception:
                    if on_error:
                        self._invoke_main(on_error, sys.exc_info())
                else:
                    if on_success:
                        self._invoke_main(on_success, result)
            try:
                if on_done:
                    self._invoke_main(on_done, None if f.cancelled() else result)
            finally:
                cb = self._tasks.pop(f, None)
                if cb:
                    self._invoke_main(cb)

        fut.add_done_callback(_handle)
        return fut

    def cancel_task(self, fut: Future[Any]) -> None:
        fut.cancel()
        cb = self._tasks.pop(fut, None)
        if cb:
            self._invoke_main(cb)

    def stop(self, timeout: float | None = 5.0) -> None:
        # Cancel all pending user-provided cancel callbacks
        for fut in list(self._tasks):
            self.cancel_task(fut)

        loop, thread = self._loop, self._thread
        if not loop or not thread:
            return

        if loop.is_running():
            # 1) Graceful shutdown inside the loop
            async def _graceful():
                current = asyncio.current_task()
                # Py3.12+: all_tasks() has no loop param
                tasks = [t for t in asyncio.all_tasks() if t is not current]
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                try:
                    await loop.shutdown_asyncgens()
                except Exception:
                    pass
                try:
                    await loop.shutdown_default_executor()
                except Exception:
                    pass

            fut = asyncio.run_coroutine_threadsafe(_graceful(), loop)
            try:
                fut.result(timeout=timeout)
            except Exception as e:
                logger.warning("Graceful shutdown timed out or failed: %r", e)

            # 2) Stop the loop and wait for the thread to exit
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=timeout)

            if thread.is_alive() or loop.is_running():
                logger.error("Event loop thread did not stop; skipping close to avoid RuntimeError")
                return

        # 3) Safe to close
        loop.close()
        self._loop = None
        self._thread = None

    async def _shutdown_coroutines(self):
        """
        Cancel all running asyncio tasks in this loop except the current one,
        then await their completion (collecting exceptions).
        """
        current = asyncio.current_task()
        tasks = [t for t in asyncio.all_tasks(loop=self._loop) if t is not current]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _invoke_main(func: Callable, *args):
        _GUI_INVOKER.invoke.emit(func, args)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

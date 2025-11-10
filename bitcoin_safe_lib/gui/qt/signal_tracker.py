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


from __future__ import annotations

import logging
from typing import Any, Callable, List, ParamSpec, Protocol, cast, runtime_checkable

from PyQt6.QtCore import QObject

logger = logging.getLogger(__name__)


P = ParamSpec("P")


@runtime_checkable
class SignalProtocol(Protocol[P]):
    def connect(self, slot: Callable[P, Any] | "SignalProtocol[P]") -> Any:
        ...

    def disconnect(self, slot: Callable[P, Any] | "SignalProtocol[P]" | None = None) -> Any:
        ...

    emit: Callable[P, Any]


class SignalTools:
    @classmethod
    def disconnect_all_signals_from(cls, object_with_bound_signals: QObject) -> None:
        """Finds any qtBoundSignal (or TypedPyQtSignal) on the given QObject
        and removes all of its connections.
        """

        def _safe_disconnect(signal: SignalProtocol) -> None:
            # disconnect() without args breaks one connection at a time
            while True:
                try:
                    signal.disconnect()
                except TypeError:
                    break

        for name in dir(object_with_bound_signals):
            if name == "destroyed":
                continue
            try:
                sig = getattr(object_with_bound_signals, name)
            except Exception:
                continue
            if isinstance(sig, SignalProtocol):
                _safe_disconnect(sig)

    @classmethod
    def connect_signal(
        cls,
        signal: SignalProtocol[P],
        handler: Callable[P, Any],
    ) -> tuple[SignalProtocol[P], Callable[P, Any]]:
        signal.connect(handler)
        return (signal, handler)

    @classmethod
    def connect_signal_and_append(
        cls,
        connected: List[tuple[SignalProtocol[Any], Callable[..., Any] | SignalProtocol[Any]]],
        signal: SignalProtocol[P],
        handler: Callable[P, Any],
    ) -> None:
        signal.connect(handler)
        erased_sig = cast(SignalProtocol[Any], signal)
        connected.append((erased_sig, handler))

    @classmethod
    def disconnect_signal(
        cls,
        signal: SignalProtocol[Any],
        handler: Callable[..., Any] | SignalProtocol[Any] | None,
    ) -> None:
        try:
            signal.disconnect(handler)
        except Exception:
            logger.debug(f"Could not disconnect {signal!r} from {handler!r}")

    @classmethod
    def disconnect_signals(
        cls,
        connected: List[tuple[SignalProtocol[Any], Callable[..., Any] | SignalProtocol[Any]]],
    ) -> None:
        while connected:
            sig, handler = connected.pop()
            cls.disconnect_signal(sig, handler)


class SignalTracker:
    def __init__(self) -> None:
        self._connected_signals: list[
            tuple[SignalProtocol[Any], Callable[..., Any] | SignalProtocol[Any]]
        ] = []

    def connect(
        self, signal: SignalProtocol[P], handler: Callable[P, Any] | SignalProtocol[P], *args, **kwargs
    ) -> None:
        # precise check happens here
        signal.connect(handler, *args, **kwargs)
        # erase ParamSpec for storage (ParamSpec is invariant)
        erased_sig = cast(SignalProtocol[Any], signal)
        erased_handler = cast(SignalProtocol[Any], handler)
        self._connected_signals.append((erased_sig, erased_handler))

    def disconnect_all(self) -> None:
        SignalTools.disconnect_signals(self._connected_signals)

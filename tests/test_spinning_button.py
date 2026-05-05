from types import SimpleNamespace
from typing import Any, cast

from bitcoin_safe_lib.gui.qt.spinning_button import SpinningButton


class TimerStub:
    def __init__(self, active: bool) -> None:
        self.active = active

    def isActive(self) -> bool:
        return self.active

    def stop(self) -> None:
        self.active = False


def test_cleanup_before_deletion_stops_timers_and_disconnects_stop_signal() -> None:
    disconnected: list[tuple[object, object]] = []
    stop_signal = object()
    enable_button = object()
    button = SimpleNamespace(
        _spinning=True,
        _stop_signal=stop_signal,
        timer=TimerStub(active=True),
        timeout_timer=TimerStub(active=True),
        enable_button=enable_button,
        _disconnect_signal=lambda signal, slot: disconnected.append((signal, slot)),
    )

    SpinningButton._cleanup_before_deletion(cast(Any, button))

    assert button._spinning is False
    assert button._stop_signal is None
    assert disconnected == [(stop_signal, enable_button)]
    assert button.timer.isActive() is False
    assert button.timeout_timer.isActive() is False


def test_rotate_svg_returns_immediately_for_deleted_wrapper() -> None:
    button = SimpleNamespace(
        _is_deleted=lambda: True,
        _spinning=True,
        timer=TimerStub(active=True),
        rotation_angle=0,
    )

    SpinningButton.rotate_svg(cast(Any, button))

    assert button.rotation_angle == 0
    assert button.timer.isActive() is True


def test_enable_button_returns_immediately_for_deleted_wrapper() -> None:
    button = SimpleNamespace(_is_deleted=lambda: True)

    SpinningButton.enable_button(cast(Any, button))

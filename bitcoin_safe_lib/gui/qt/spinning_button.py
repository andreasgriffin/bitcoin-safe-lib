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


import os
import sys
from typing import Optional

from PyQt6.QtCore import QByteArray, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from bitcoin_safe_lib.gui.qt.icons import SvgTools
from bitcoin_safe_lib.gui.qt.signal_tracker import SignalProtocol


def resource_path(*parts: str) -> str:
    pkg_dir = os.path.split(os.path.realpath(__file__))[0]
    return os.path.join(pkg_dir, *parts)


def icon_path(icon_basename: str) -> str:
    return resource_path("icons", icon_basename)


DEFAULT_ENABLED_ICON = QIcon()
DEFAULT_SPINNER_SVG = """
<svg viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
  <circle cx="25" cy="25" r="20"
          fill="none"
          stroke="currentColor"
          stroke-width="4"
          stroke-linecap="round"
          stroke-dasharray="31.4 31.4"/>
</svg>
"""


class SpinningButton(QPushButton):
    """
    A QPushButton that, when clicked, can show a spinning SVG icon
    until either:
      - signal_stop_spinning is emitted, or
      - timeout is reached, or
      - enable_button() is called manually.
    """

    signal_started_spinning = pyqtSignal()
    signal_stopped_spinning = pyqtSignal()

    def __init__(
        self,
        text: str,
        signal_stop_spinning: Optional[SignalProtocol] = None,
        enabled_icon: QIcon = DEFAULT_ENABLED_ICON,
        spinning_svg_content: str | None = None,
        parent=None,
        timeout: int = 60,
        disable_while_spinning: bool = True,
    ) -> None:
        super().__init__(text, parent)

        self.disable_while_spinning = disable_while_spinning

        spinning_svg_content = spinning_svg_content if spinning_svg_content else DEFAULT_SPINNER_SVG
        self.svg_renderer = QSvgRenderer(QByteArray(spinning_svg_content.encode("utf-8")))

        if not self.svg_renderer.isValid():
            raise ValueError("Invalid SVG content provided")

        self.rotation_angle = 0
        self._icon_size = QSize(18, 18)
        self.padding = 3
        self.timeout = timeout

        self.enabled_icon = enabled_icon
        self.setIcon(self.enabled_icon)

        self._spinning = False
        self._stop_signal: SignalProtocol | None = None

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.rotate_svg)

        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.enable_button)

        self.clicked.connect(self.on_clicked)

        if signal_stop_spinning is not None:
            self.set_enable_signal(signal_stop_spinning)

    def start_spin(self) -> None:
        """Idempotent: safe to call multiple times."""
        if self._spinning:
            if not self.timer.isActive():
                self.timer.start()
            if self.timeout > 0 and not self.timeout_timer.isActive():
                self.timeout_timer.start(self.timeout * 1000)
            return

        self._spinning = True
        self.rotation_angle = 0

        # Show spinner as the *actual* icon so Qt positions it correctly
        self.setIcon(self._spinner_icon(0))

        # Optionally disable while spinning
        if self.disable_while_spinning and self.isEnabled():
            self.setDisabled(True)

        if not self.timer.isActive():
            self.timer.start()

        if self.timeout > 0:
            self.timeout_timer.start(self.timeout * 1000)

        self.signal_started_spinning.emit()
        self.update()

    def enable_button(self, *args, **kwargs) -> None:
        """Idempotent: safe to call multiple times."""
        if self.timer.isActive():
            self.timer.stop()
        if self.timeout_timer.isActive():
            self.timeout_timer.stop()

        was_spinning = self._spinning
        self._spinning = False

        self.setIcon(self.enabled_icon)

        # If we disabled during spinning, re-enable
        if self.disable_while_spinning and not self.isEnabled():
            self.setEnabled(True)

        if was_spinning:
            self.signal_stopped_spinning.emit()
            self.update()

    def _disconnect_signal(self, signal: SignalProtocol, slot) -> None:
        """
        Best-effort disconnect helper.
        Safely ignores cases where the signal is not connected
        or is not a Qt-like signal.
        """
        try:
            signal.disconnect(slot)
        except Exception:
            pass

    def set_enable_signal(self, signal_stop_spinning: SignalProtocol | None) -> None:
        """
        Robustly (re)binds the external stop-spinning signal.
        """
        # Unbind old signal
        if self._stop_signal:
            self._disconnect_signal(self._stop_signal, self.enable_button)
        self._stop_signal = None

        if signal_stop_spinning is None:
            return

        self._stop_signal = signal_stop_spinning
        self._disconnect_signal(self._stop_signal, self.enable_button)
        try:
            self._stop_signal.connect(self.enable_button)  # type: ignore[attr-defined]
        except Exception:
            self._stop_signal = None

    def on_clicked(self) -> None:
        if not self.isEnabled():
            return
        self.start_spin()

    def rotate_svg(self) -> None:
        if not self._spinning:
            if self.timer.isActive():
                self.timer.stop()
            return

        self.rotation_angle = (self.rotation_angle + 10) % 360
        self.setIcon(self._spinner_icon(self.rotation_angle))

    def _spinner_icon(self, angle: float) -> QIcon:
        size = self.iconSize()
        dpr = self.devicePixelRatioF()

        pm = QPixmap(int(size.width() * dpr), int(size.height() * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = size.width() / 2
        cy = size.height() / 2
        p.translate(cx, cy)
        p.rotate(angle)
        p.translate(-cx, -cy)

        self.svg_renderer.render(p, QRectF(0, 0, size.width(), size.height()))
        p.end()

        return QIcon(pm)

    def setIconSize(self, size: QSize) -> None:
        if not isinstance(size, QSize):
            raise TypeError("Size must be a QSize object")
        self._icon_size = size
        self.update()

    def iconSize(self) -> QSize:
        return self._icon_size

    def sizeHint(self) -> QSize:
        default_size_hint = super().sizeHint()
        total_width = default_size_hint.width() + self._icon_size.width() + 2 * self.padding
        total_height = max(default_size_hint.height(), self._icon_size.height())
        return QSize(total_width, total_height)


if __name__ == "__main__":

    def get_icon_path(icon_basename: str) -> str:
        """Get icon path."""
        return resource_path("icons", icon_basename)

    svg_tools = SvgTools(get_icon_path=get_icon_path, theme_file=get_icon_path("theme.csv"))

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()

            self.button = SpinningButton(
                "testing",
                enabled_icon=svg_tools.svg_to_icon(DEFAULT_SPINNER_SVG),
                timeout=3,
            )

            self.button.signal_started_spinning.connect(lambda: print("signal_started_spinning"))
            self.button.signal_stopped_spinning.connect(lambda: print("signal_stopped_spinning"))

            layout = QVBoxLayout()
            layout.addWidget(self.button)

            central_widget = QWidget()
            central_widget.setLayout(layout)
            self.setCentralWidget(central_widget)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

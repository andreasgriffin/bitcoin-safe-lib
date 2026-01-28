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


import logging
from datetime import datetime, timedelta

from PyQt6.QtCore import QByteArray
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QAbstractButton, QApplication, QMessageBox, QPushButton

from .i18n import translate

logger = logging.getLogger(__name__)


def is_dark_mode() -> bool:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return False

    palette = app.palette()
    background_color = palette.color(QPalette.ColorRole.Window)
    text_color = palette.color(QPalette.ColorRole.WindowText)

    # Check if the background color is darker than the text color
    return background_color.lightness() < text_color.lightness()


def adjust_brightness(color: QColor, value: float) -> QColor:
    """
    Adjust the brightness of a QColor.

    Parameters:
        color (QColor): The original color to adjust.
        value (float): The brightness adjustment factor, ranging from -1.0 to 1.0.
                       -1.0 makes the color completely black,
                        1.0 makes the color completely white,
                        0.0 leaves the color unchanged.

    Returns:
        QColor: A new QColor with the adjusted brightness.
    """
    if not -1.0 <= value <= 1.0:
        raise ValueError("The value must be between -1.0 and 1.0.")

    # Get the current RGB values
    _r, _, _, a = color.red(), color.green(), color.blue(), color.alpha()

    # Convert RGB to HSV (Hue, Saturation, Value)
    hsv_color = color.toHsv()
    h, s, v = hsv_color.hue(), hsv_color.saturation(), hsv_color.value()

    # Adjust the value (brightness)
    new_v = max(0, min(255, v + value * 255))

    # Create a new QColor with the adjusted brightness
    new_color = QColor()
    new_color.setHsv(h, s, int(new_v), a)

    return new_color


def age(
    from_date: int | float | None | timedelta,  # POSIX timestamp
    *,
    since_date: datetime | None = None,
    target_tz=None,
    include_seconds: bool = False,
) -> str:
    """Takes a timestamp and returns a string with the approximation of the
    age."""
    if from_date is None:
        return translate("util", "Unknown")

    if since_date is None:
        since_date = datetime.now(target_tz)

    from_date_clean = (
        since_date + from_date if isinstance(from_date, timedelta) else datetime.fromtimestamp(from_date)
    )

    distance_in_time = from_date_clean - since_date
    is_in_past = from_date_clean < since_date
    distance_in_seconds = int(round(abs(distance_in_time.days * 86400 + distance_in_time.seconds)))
    distance_in_minutes = int(round(distance_in_seconds / 60))

    if distance_in_minutes == 0:
        if include_seconds:
            if is_in_past:
                return translate("util", "{} seconds ago").format(distance_in_seconds)
            else:
                return translate("util", "in {} seconds").format(distance_in_seconds)
        else:
            if is_in_past:
                return translate("util", "less than a minute ago")
            else:
                return translate("util", "in less than a minute")
    elif distance_in_minutes < 45:
        if is_in_past:
            return translate("util", "about {} minutes ago").format(distance_in_minutes)
        else:
            return translate("util", "in about {} minutes").format(distance_in_minutes)
    elif distance_in_minutes < 90:
        if is_in_past:
            return translate("util", "about 1 hour ago")
        else:
            return translate("util", "in about 1 hour")
    elif distance_in_minutes < 1440:
        if is_in_past:
            return translate("util", "about {} hours ago").format(round(distance_in_minutes / 60.0))
        else:
            return translate("util", "in about {} hours").format(round(distance_in_minutes / 60.0))
    elif distance_in_minutes < 2880:
        if is_in_past:
            return translate("util", "about 1 day ago")
        else:
            return translate("util", "in about 1 day")
    elif distance_in_minutes < 43220:
        if is_in_past:
            return translate("util", "about {} days ago").format(round(distance_in_minutes / 1440))
        else:
            return translate("util", "in about {} days").format(round(distance_in_minutes / 1440))
    elif distance_in_minutes < 86400:
        if is_in_past:
            return translate("util", "about 1 month ago")
        else:
            return translate("util", "in about 1 month")
    elif distance_in_minutes < 525600:
        if is_in_past:
            return translate("util", "about {} months ago").format(round(distance_in_minutes / 43200))
        else:
            return translate("util", "in about {} months").format(round(distance_in_minutes / 43200))
    elif distance_in_minutes < 1051200:
        if is_in_past:
            return translate("util", "about 1 year ago")
        else:
            return translate("util", "in about 1 year")
    else:
        if is_in_past:
            return translate("util", "over {} years ago").format(round(distance_in_minutes / 525600))
        else:
            return translate("util", "in over {} years").format(round(distance_in_minutes / 525600))


def confirmation_wait_formatted(projected_mempool_block_index: int):
    estimated_duration = timedelta(minutes=projected_mempool_block_index * 10)
    estimated_duration = max(estimated_duration, timedelta(minutes=10))

    return age(estimated_duration)


def qbytearray_to_str(a: QByteArray) -> str:
    return a.data().decode()


def str_to_qbytearray(s: str) -> QByteArray:
    return QByteArray(s.encode())  # type: ignore[call-overload]


def question_dialog(
    text: str = "",
    title: str = "Question",
    true_button: QMessageBox.StandardButton | QPushButton | str = QMessageBox.StandardButton.Yes,
    false_button: QMessageBox.StandardButton | QPushButton | str = QMessageBox.StandardButton.Cancel,
    default_is_true_button: bool = True,
) -> bool | None:
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Question)

    # map the actual QPushButton instance back to True/False
    button_map: dict[QAbstractButton | None, bool] = {}

    def _add(
        btn_def: QMessageBox.StandardButton | QPushButton | str, role: QMessageBox.ButtonRole
    ) -> QPushButton | None:
        # 1) If user passed a str, make a QPushButton
        btn: QPushButton | None = None
        if isinstance(btn_def, str):
            btn = QPushButton(btn_def)
            msg.addButton(btn, role)

        # 2) If user passed a QPushButton, use it directly
        elif isinstance(btn_def, QPushButton):
            btn = btn_def
            msg.addButton(btn, role)

        # 3) Otherwise it must be a StandardButton enum
        else:
            # addButton(StandardButton, ButtonRole) returns the created QPushButton
            btn = msg.addButton(btn_def)

        # remember which choice this represents
        button_map[btn] = role == QMessageBox.ButtonRole.AcceptRole
        return btn

    # add both buttons (and keep hold of the actual instances)
    true_btn = _add(true_button, QMessageBox.ButtonRole.AcceptRole)
    false_btn = _add(false_button, QMessageBox.ButtonRole.RejectRole)

    # set the default button to our "true" button instance
    msg.setDefaultButton(true_btn if default_is_true_button else false_btn)

    # run the dialog
    msg.exec()
    clicked = msg.clickedButton()

    # translate back to True/False/None
    return button_map.get(clicked, None)

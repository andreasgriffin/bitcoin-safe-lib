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

import csv
import gzip
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional, Tuple

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

from .util import is_dark_mode


class SvgTools:
    def __init__(self, get_icon_path: Callable[[str], str], theme_file: str | None) -> None:
        self.get_icon_path = get_icon_path
        self.theme_file = theme_file

    @classmethod
    def read_source_file(cls, svg_path: str) -> str:
        if svg_path.lower().endswith(".svgz"):
            # Open the svgz file in text mode with gzip
            with gzip.open(svg_path, "rt", encoding="utf-8") as file:
                return file.read()
        else:
            # Open the file normally
            with open(svg_path, "r", encoding="utf-8") as file:
                return file.read()

    def auto_theme_svg(self, svg_content: str, color: QColor | None = None) -> str:
        csv_rows = []
        if self.theme_file:
            with open(self.theme_file, "r") as file:
                csv_reader = csv.reader(file)
                all_rows = [row for row in csv_reader if row]
                header, csv_rows = all_rows[0], all_rows[1:]

        if color is None:
            color = QApplication.palette().color(QPalette.ColorRole.WindowText)
        # Replace "currentColor" in the SVG with the desired color
        replace_strings = csv_rows + [["WindowText", color.name(), color.name()]]

        for org, light_mode, dark_mode in replace_strings:
            svg_content = svg_content.replace(org, dark_mode if is_dark_mode() else light_mode)
        return svg_content

    @classmethod
    def svg_to_pixmap(cls, svg_data: str, size=(256, 256)) -> QPixmap:
        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
        tgt_w, tgt_h = size

        # Get the SVG's natural size
        src_size = renderer.defaultSize()
        if src_size.width() <= 0 or src_size.height() <= 0:
            vb = renderer.viewBoxF()
            src_w, src_h = vb.width(), vb.height()
        else:
            src_w, src_h = float(src_size.width()), float(src_size.height())

        if src_w <= 0 or src_h <= 0:
            src_w = src_h = 1.0  # avoid div-by-zero for odd SVGs

        # Scale to *fit* (inscribe) while preserving aspect ratio
        scale = min(tgt_w / src_w, tgt_h / src_h)
        w, h = src_w * scale, src_h * scale
        x, y = (tgt_w - w) / 2.0, (tgt_h - h) / 2.0

        pixmap = QPixmap(tgt_w, tgt_h)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter, QRectF(x, y, w, h))  # draw into the centered, scaled rect
        painter.end()
        return pixmap

    @classmethod
    def svg_to_icon(cls, svg_content: str, size=(256, 256)) -> QIcon:
        # Create an icon from the pixmap
        pixmap = cls.svg_to_pixmap(svg_content, size)
        return QIcon(pixmap)

    def get_svg_content(
        self,
        icon_basename: Optional[str],
        auto_theme: bool = True,
        replace_tuples: Optional[Tuple[Tuple[str, str], ...]] = None,
    ) -> str:
        if not icon_basename:
            return ""
        icon_file = Path(self.get_icon_path(icon_basename))
        if not icon_file.exists():
            return ""

        if icon_file.suffix.lstrip(".") in ["svg", "svgz"]:
            svg_content = self.read_source_file(str(icon_file))

            if replace_tuples:
                for old_text, new_text in replace_tuples:
                    svg_content = svg_content.replace(old_text, new_text)

            return self.auto_theme_svg(svg_content) if auto_theme else svg_content
        else:
            return ""

    @lru_cache(maxsize=1000)
    def get_QIcon(
        self,
        icon_basename: Optional[str],
        auto_theme: bool = True,
        size: Tuple[int, int] = (256, 256),
        replace_tuples: Optional[Tuple[Tuple[str, str], ...]] = None,
    ) -> QIcon:
        svg_content = self.get_svg_content(
            icon_basename=icon_basename, auto_theme=auto_theme, replace_tuples=replace_tuples
        )
        if not svg_content:
            return QIcon()
        return self.svg_to_icon(svg_content, size=size)

    @lru_cache(maxsize=1000)
    def get_pixmap(
        self,
        icon_basename: Optional[str],
        auto_theme: bool = True,
        size: Tuple[int, int] = (256, 256),
        replace_tuples: Optional[Tuple[Tuple[str, str], ...]] = None,
    ) -> QPixmap:
        svg_content = self.get_svg_content(
            icon_basename=icon_basename, auto_theme=auto_theme, replace_tuples=replace_tuples
        )
        if not svg_content:
            return QPixmap()

        return self.svg_to_pixmap(svg_content, size=size)

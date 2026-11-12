from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

from bitcoin_safe_lib.gui.qt.icons import SvgTools


@pytest.fixture()
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


def write_icon(directory: Path, name: str, content: str) -> Path:
    icon_file = directory / name
    icon_file.write_text(content, encoding="utf-8")
    return icon_file


def test_get_svg_content_caches_reads(tmp_path: Path, qapp: QApplication) -> None:
    icon_file = write_icon(tmp_path, "icon.svg", "<svg>content</svg>")
    svg_tools = SvgTools(get_icon_path=lambda basename: str(tmp_path / basename), theme_file=None)

    with pytest.MonkeyPatch.context() as monkeypatch:
        reads: list[str] = []
        original_read = SvgTools.read_source_file

        def counting_read(svg_path: str) -> str:
            reads.append(svg_path)
            return original_read(svg_path)

        monkeypatch.setattr(SvgTools, "read_source_file", staticmethod(counting_read))

        first = svg_tools.get_svg_content("icon.svg")
        second = svg_tools.get_svg_content("icon.svg")

    assert first == second == "<svg>content</svg>"
    assert reads == [str(icon_file)]


def test_get_svg_content_rethemes_on_palette_change(tmp_path: Path, qapp: QApplication) -> None:
    write_icon(tmp_path, "icon.svg", "<svg>currentColor</svg>")
    svg_tools = SvgTools(get_icon_path=lambda basename: str(tmp_path / basename), theme_file=None)

    original_palette = QPalette(qapp.palette())

    def two_color_palette(window: Qt.GlobalColor, window_text: Qt.GlobalColor) -> QPalette:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, window)
        palette.setColor(QPalette.ColorRole.WindowText, window_text)
        return palette

    try:
        qapp.setPalette(two_color_palette(Qt.GlobalColor.white, Qt.GlobalColor.black))
        light_content = svg_tools.get_svg_content("icon.svg")

        qapp.setPalette(two_color_palette(Qt.GlobalColor.black, Qt.GlobalColor.white))
        dark_content = svg_tools.get_svg_content("icon.svg")
    finally:
        qapp.setPalette(original_palette)

    assert light_content != dark_content
    assert "currentColor" not in light_content
    assert "currentColor" not in dark_content


def test_get_svg_content_applies_replace_tuples(tmp_path: Path, qapp: QApplication) -> None:
    write_icon(tmp_path, "icon.svg", "<svg>foo</svg>")
    svg_tools = SvgTools(get_icon_path=lambda basename: str(tmp_path / basename), theme_file=None)

    replaced = svg_tools.get_svg_content("icon.svg", auto_theme=False, replace_tuples=(("foo", "bar"),))
    unchanged = svg_tools.get_svg_content("icon.svg", auto_theme=False)

    assert replaced == "<svg>bar</svg>"
    assert unchanged == "<svg>foo</svg>"


def test_get_svg_content_returns_empty_for_missing_and_non_svg(tmp_path: Path, qapp: QApplication) -> None:
    write_icon(tmp_path, "icon.txt", "<svg>foo</svg>")
    svg_tools = SvgTools(get_icon_path=lambda basename: str(tmp_path / basename), theme_file=None)

    assert svg_tools.get_svg_content("missing.svg") == ""
    assert svg_tools.get_svg_content(None) == ""
    assert svg_tools.get_svg_content("icon.txt") == ""


def test_theme_rows_are_not_mutated_by_theming(tmp_path: Path, qapp: QApplication) -> None:
    theme_file = tmp_path / "theme.csv"
    theme_file.write_text("org,light,dark\nfoo,black,white\n", encoding="utf-8")
    write_icon(tmp_path, "icon.svg", "<svg>foo</svg>")
    svg_tools = SvgTools(get_icon_path=lambda basename: str(tmp_path / basename), theme_file=str(theme_file))

    first = svg_tools.auto_theme_svg("<svg>foo</svg>")
    second = svg_tools.auto_theme_svg("<svg>foo</svg>")

    assert first == second
    assert svg_tools._get_theme_rows() == [["foo", "black", "white"]]

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


import hashlib
import logging
import re
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Literal,
    TypeVar,
)

import numpy as np

logger = logging.getLogger(__name__)


T = TypeVar("T")
T2 = TypeVar("T2")


def is_int(a: Any) -> bool:
    try:
        int(a)
    except Exception:
        return False
    return True


def path_to_rel_home_path(path: Path | str) -> Path:
    try:
        return Path(path).relative_to(Path.home())
    except Exception as e:
        logger.debug(str(e))
        return Path(path)


def rel_home_path_to_abs_path(rel_home_path: Path | str) -> Path:
    return Path.home() / rel_home_path


def compare_dictionaries(dict1: dict, dict2: dict):
    # Get unique keys from both dictionaries
    unique_keys = set(dict1.keys()) ^ set(dict2.keys())

    # Get keys with different values
    differing_values = {k for k in dict1 if k in dict2 and dict1[k] != dict2[k]}

    # Combine unique keys and differing values
    keys_to_include = unique_keys | differing_values

    # Create a new dictionary with only the differing entries
    result = {k: dict1.get(k, dict2.get(k)) for k in keys_to_include}

    return result


def inv_dict(d: dict):
    return {v: k for k, v in d.items()}


def all_subclasses(cls) -> set:
    """Return all (transitive) subclasses of cls."""
    res = set(cls.__subclasses__())
    for sub in res.copy():
        res |= all_subclasses(sub)
    return res


def replace_non_alphanumeric(string: str):
    return re.sub(r"\W+", "_", string)


def hash_string(text: str):
    return hashlib.sha256(text.encode()).hexdigest()


def is_iterable(obj):
    return hasattr(obj, "__iter__") or hasattr(obj, "__getitem__")


def time_logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time

        message = f"Function {func.__qualname__} needed {duration:.3f}s"
        if duration < 5e-2:
            logger.debug(message)
        else:
            logger.info(message)

        return result

    return wrapper


def threadtable(f, arglist, max_workers=20):
    with ThreadPoolExecutor(max_workers=int(max_workers)) as executor:
        logger.debug(f"Starting {max_workers} threads {str(f)}({str(arglist)})")
        res = []
        for arg in arglist:
            res.append(executor.submit(f, arg))
    return [r.result() for r in res]


@time_logger
def threadtable_batched(f: Callable[[T], T2], txs: list[T], number_chunks=8) -> list[T2]:
    chunks = np.array_split(np.array(txs), number_chunks)

    def batched_f(txs):
        return [f(tx) for tx in txs]

    result = threadtable(batched_f, chunks, max_workers=number_chunks)
    return sum(result, [])


def clean_dict(d: dict):
    return {k: v for k, v in d.items() if v}


# ruff: noqa: UP047
def clean_list(item: Iterable[T | None]) -> list[T]:
    "removes none, 0 or '' items off a list"
    return [v for v in item if v]


def remove_duplicates_keep_order(seq):
    seen = set()
    result = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# Helper function to lighten a color
def lighten_color(hex_color: str, factor: float):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_ansi(hex_color: str):
    """Convert hex color to closest ANSI color."""
    # Mapping of ANSI color codes to RGB values
    ansi_colors = {
        30: (0, 0, 0),  # Black
        31: (128, 0, 0),  # Red
        32: (0, 128, 0),  # Green
        33: (128, 128, 0),  # Yellow
        34: (0, 0, 128),  # Blue
        35: (128, 0, 128),  # Magenta
        36: (0, 128, 128),  # Cyan
        37: (192, 192, 192),  # Light gray
        90: (128, 128, 128),  # Dark gray
        91: (255, 0, 0),  # Light red
        92: (0, 255, 0),  # Light green
        93: (255, 255, 0),  # Light yellow
        94: (0, 0, 255),  # Light blue
        95: (255, 0, 255),  # Light magenta
        96: (0, 255, 255),  # Light cyan
        97: (255, 255, 255),  # White
    }

    # Convert hex to RGB
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)

    # Find the closest ANSI color
    closest_ansi = min(
        ansi_colors,
        key=lambda k: (r - ansi_colors[k][0]) ** 2
        + (g - ansi_colors[k][1]) ** 2
        + (b - ansi_colors[k][2]) ** 2,
    )
    return closest_ansi


# New function to apply color formatting to a string
def color_format_str(
    s, hex_color="#000000", color_formatting: Literal["html", "rich", "bash"] | None = "rich"
):
    if hex_color == "#000000":
        return s
    if color_formatting == "html":
        return f'<span style="color:{hex_color}">{s}</span>'
    if color_formatting == "rich":
        return f'<font color="{hex_color}">{s}</font>'
    if color_formatting == "bash":
        ansi_code = hex_to_ansi(hex_color)
        return f"\033[{ansi_code}m{s}\033[0m"

    return s


def unique_elements(iterable: Iterable):
    return list(dict.fromkeys(iterable))


def insert_invisible_spaces_for_wordwrap(s: str, max_word_length: int = 20) -> str:
    """
    Insert zero-width spaces (\u200b) into any word in `s` that exceeds max_word_length,
    so that it can be wrapped by browsers or text renderers.

    :param s: Input string.
    :param max_word_length: Maximum allowed length of a continuous word before inserting \u200b.
    :return: Modified string with \u200b inserted into long words.
    """
    words = s.split(" ")
    processed = []

    for word in words:
        if len(word) <= max_word_length:
            # Short enough, leave as-is
            processed.append(word)
        else:
            # Break the word into chunks of max_word_length
            parts = [word[i : i + max_word_length] for i in range(0, len(word), max_word_length)]
            # Rejoin with zero-width spaces between chunks
            processed.append("\u200b".join(parts))

    return " ".join(processed)

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


import enum
import logging
from typing import Literal, Union

import bdkpython as bdk
from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QColor

from bitcoin_safe_lib.caching import register_cache
from bitcoin_safe_lib.gui.qt.i18n import translate
from bitcoin_safe_lib.gui.qt.util import adjust_brightness, is_dark_mode
from bitcoin_safe_lib.util import color_format_str

logger = logging.getLogger(__name__)


class SatSymbol(enum.Enum):
    Sat = "Sat"
    UNICODE = "⚡"


class BitcoinSymbol(enum.Enum):
    ISO = "BTC"
    UNICODE = "₿"


def unit_str(network: bdk.Network, btc_symbol: str = BitcoinSymbol.ISO.value) -> str:
    return btc_symbol if network is None or network == bdk.Network.BITCOIN else f"t{btc_symbol}"


def unit_sat_str(network: bdk.Network, sat_symbol: str = SatSymbol.Sat.value) -> str:
    return sat_symbol if network is None or network == bdk.Network.BITCOIN else f"t{sat_symbol}"


def unit_fee_str(network: bdk.Network, sat_symbol: str = SatSymbol.Sat.value) -> str:
    "Sat/vB"
    return f"{sat_symbol}/vB" if network is None or network == bdk.Network.BITCOIN else f"t{sat_symbol}/vB"


def format_fee_rate_splitted(
    fee_rate: float, network: bdk.Network, sat_symbol: str = SatSymbol.Sat.value
) -> tuple[float, str]:
    return round(fee_rate, 1), unit_fee_str(network, sat_symbol=sat_symbol)


def format_fee_rate(fee_rate: float, network: bdk.Network, sat_symbol: str = SatSymbol.Sat.value) -> str:
    fee, unit = format_fee_rate_splitted(fee_rate=fee_rate, network=network, sat_symbol=sat_symbol)
    return f"{fee} {unit}"


# Main formatting function
@register_cache()
def format_number(
    number,
    color_formatting: Literal["html", "rich", "bash"] | None = None,
    include_decimal_spaces=True,
    base_color="#000000",
    indicate_balance_change=False,
    unicode_space_character=None,
):
    number = int(number)
    # Split into integer and decimal parts
    integer_part, decimal_part = f"{number / 1e8:.8f}".split(".")

    # Format the integer part with commas or OS native separators
    abs_integer_part_formatted = QLocale().toString(abs(int(integer_part)))

    # Split the decimal part into groups
    decimal_groups = [decimal_part[:2], decimal_part[2:5], decimal_part[5:]]

    # Determine color for negative numbers if indicated
    overall_color = (
        "#ff0000" if indicate_balance_change and number < 0 and base_color == "#000000" else base_color
    )

    # Apply color formatting to decimal groups
    if color_formatting:
        lighter_color = adjust_brightness(QColor(overall_color), 0.3 * (-1 if is_dark_mode() else 1)).name()
        lightest_color = adjust_brightness(QColor(overall_color), 0.5 * (-1 if is_dark_mode() else 1)).name()

        for i in range(len(decimal_groups)):
            if i == len(decimal_groups) - 1:
                color = lightest_color
            elif i == len(decimal_groups) - 2:
                color = lighter_color
            else:
                color = overall_color

            decimal_groups[i] = color_format_str(decimal_groups[i], color, color_formatting)

    # No color formatting applied if color_formatting is None
    space_character = "\u00a0" if unicode_space_character else " "
    decimal_part_formatted = (
        space_character.join(decimal_groups) if include_decimal_spaces else "".join(decimal_groups)
    )

    integer_part_formatted = abs_integer_part_formatted
    if number < 0:
        integer_part_formatted = f"-{abs_integer_part_formatted}"
    if indicate_balance_change and number >= 0:
        integer_part_formatted = f"+{abs_integer_part_formatted}"

    # Combine integer and decimal parts with separator
    int_part = color_format_str(integer_part_formatted, overall_color, color_formatting)

    formatted_number = f"{int_part}{color_format_str(QLocale().decimalPoint(), overall_color, color_formatting)}{decimal_part_formatted}"

    return formatted_number


class Satoshis:
    def __init__(self, value: int | bdk.Amount, network: bdk.Network):
        self.network = network
        self.value = value.to_sat() if isinstance(value, bdk.Amount) else value

    @classmethod
    def from_btc_str(cls, s: str, network: bdk.Network, btc_symbol: str = BitcoinSymbol.ISO.value):
        f = (
            QLocale().toDouble(
                str(s).replace(unit_str(network, btc_symbol=btc_symbol), "").strip().replace(" ", "")
            )[0]
            * 1e8
        )
        value = int(round(f))
        return Satoshis(value=value, network=network)

    def __repr__(self):
        return f"Satoshis({self.value})"

    def __str__(self):
        return format_number(self.value, color_formatting=None, include_decimal_spaces=True)

    def __eq__(self, other):
        return (self.value == other.value) and (self.network == other.network)

    def __ne__(self, other):
        return not (self == other)

    def __add__(self, other: "Satoshis"):
        assert self.network == other.network
        return Satoshis(self.value + other.value, self.network)

    def format_splitted(
        self,
        color_formatting: Literal["html", "rich", "bash"] | None = "rich",
        unicode_space_character=True,
        btc_symbol: str = BitcoinSymbol.ISO.value,
    ) -> tuple[str, str]:
        number = format_number(
            self.value,
            color_formatting=color_formatting,
            include_decimal_spaces=True,
            unicode_space_character=unicode_space_character,
        )
        return number, color_format_str(
            unit_str(self.network, btc_symbol=btc_symbol), color_formatting=color_formatting
        )

    def format(
        self,
        color_formatting: Literal["html", "rich", "bash"] | None = "rich",
        show_unit=False,
        unicode_space_character=True,
        btc_symbol: str = BitcoinSymbol.ISO.value,
    ):
        number, unit = self.format_splitted(
            color_formatting=color_formatting,
            unicode_space_character=unicode_space_character,
            btc_symbol=btc_symbol,
        )
        if show_unit:
            return f"{number} {unit}"
        else:
            return number

    def str_with_unit(
        self,
        color_formatting: Literal["html", "rich", "bash"] | None = "rich",
        btc_symbol: str = BitcoinSymbol.ISO.value,
    ):
        return self.format(color_formatting=color_formatting, show_unit=True, btc_symbol=btc_symbol)

    def str_as_change(
        self,
        color_formatting: Literal["html", "rich", "bash"] | None = None,
        unit=False,
        btc_symbol: str = BitcoinSymbol.ISO.value,
    ):
        return (
            f"{format_number(self.value, color_formatting=color_formatting, include_decimal_spaces=True, indicate_balance_change=True)}"
            + (
                f" {color_format_str(unit_str(self.network, btc_symbol=btc_symbol), color_formatting=color_formatting)}"
                if unit
                else ""
            )
        )

    def format_as_balance(self, btc_symbol: str = BitcoinSymbol.ISO.value):
        return translate("util", "Balance: {amount}").format(amount=self.str_with_unit(btc_symbol=btc_symbol))

    def __bool__(self):
        return bool(self.value)

    @classmethod
    def sum(cls, obj: Union[list, tuple, "Satoshis"]) -> "Satoshis":
        def calc_satoshi(v: Union[list, tuple, "Satoshis"]) -> Satoshis:
            # allow recursive summing
            return Satoshis.sum(v) if isinstance(v, (list, tuple)) else v

        if not obj:
            raise ValueError("Cannot sum an empty list")
        if isinstance(obj, Satoshis):
            return obj

        summed = calc_satoshi(obj[0])
        for v in obj[1:]:
            summed += calc_satoshi(v)

        return summed

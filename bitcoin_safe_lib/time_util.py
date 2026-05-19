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

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from bitcoin_safe_lib.gui.qt.i18n import translate


class AgeStyle(Enum):
    RELATIVE = "relative"  # "about 3 days ago", "in about 3 days"
    PLAIN = "plain"  # "about 3 days"


class AgeUnit(Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class AgeDirection(Enum):
    PAST = "past"
    FUTURE = "future"


@dataclass(frozen=True)
class AgeDistance:
    value: int
    unit: AgeUnit
    over: bool = False


def age(
    target: datetime,
    relative_to: datetime | None = None,
    style: AgeStyle = AgeStyle.RELATIVE,
    include_seconds: bool = False,
) -> str:
    """Return a localized, human-readable approximate age for `target`.

    Args:
        target:
            The datetime to describe.

        relative_to:
            The datetime to compare against. Defaults to now.
            If omitted, uses datetime.now(target.tzinfo), so aware datetimes
            are compared against an aware "now" in the same timezone.

        style:
            AgeStyle.RELATIVE:
                "about 3 days ago"
                "in about 3 days"

            AgeStyle.PLAIN:
                "about 3 days"

        include_seconds:
            Whether values under one minute should be rendered as seconds.

    Examples:
        age(created_at)
        age(expires_at)
        age(created_at, style=AgeStyle.PLAIN)
        age(created_at, include_seconds=True)
        age(created_at, relative_to=some_other_datetime)
    """
    if relative_to is None:
        relative_to = datetime.now(target.tzinfo)

    _validate_datetime_pair(target, relative_to)

    delta = target - relative_to
    direction = AgeDirection.PAST if delta.total_seconds() < 0 else AgeDirection.FUTURE

    distance = _seconds_to_age_distance(
        int(round(abs(delta.total_seconds()))),
        include_seconds=include_seconds,
    )

    return _render_age(
        distance,
        direction=direction,
        style=style,
    )


def _validate_datetime_pair(target: datetime, relative_to: datetime) -> None:
    target_is_aware = target.tzinfo is not None and target.utcoffset() is not None
    relative_to_is_aware = relative_to.tzinfo is not None and relative_to.utcoffset() is not None

    if target_is_aware != relative_to_is_aware:
        raise ValueError("target and relative_to must both be timezone-aware or both be naive")


def _seconds_to_age_distance(
    seconds: int,
    *,
    include_seconds: bool,
) -> AgeDistance | None:
    minutes = int(round(seconds / 60))

    if minutes == 0:
        if include_seconds:
            return AgeDistance(seconds, AgeUnit.SECOND)
        return None

    if minutes < 45:
        return AgeDistance(minutes, AgeUnit.MINUTE)

    if minutes < 90:
        return AgeDistance(1, AgeUnit.HOUR)

    if minutes < 1440:
        return AgeDistance(round(minutes / 60.0), AgeUnit.HOUR)

    if minutes < 2880:
        return AgeDistance(1, AgeUnit.DAY)

    if minutes < 43220:
        return AgeDistance(round(minutes / 1440), AgeUnit.DAY)

    if minutes < 86400:
        return AgeDistance(1, AgeUnit.MONTH)

    if minutes < 525600:
        return AgeDistance(round(minutes / 43200), AgeUnit.MONTH)

    if minutes < 1051200:
        return AgeDistance(1, AgeUnit.YEAR)

    return AgeDistance(
        round(minutes / 525600),
        AgeUnit.YEAR,
        over=True,
    )


def _render_age(
    distance: AgeDistance | None,
    *,
    direction: AgeDirection,
    style: AgeStyle,
) -> str:
    if distance is None:
        if style is AgeStyle.PLAIN:
            return translate("util", "less than a minute")

        if direction is AgeDirection.PAST:
            return translate("util", "less than a minute ago")

        return translate("util", "in less than a minute")

    if style is AgeStyle.PLAIN:
        return _render_plain_age(distance)

    if direction is AgeDirection.PAST:
        return _render_past_age(distance)

    return _render_future_age(distance)


def _render_plain_age(distance: AgeDistance) -> str:
    value = distance.value

    match distance.unit:
        case AgeUnit.SECOND:
            if value == 1:
                return translate("util", "1 second")
            return translate("util", "{} seconds").format(value)

        case AgeUnit.MINUTE:
            if value == 1:
                return translate("util", "about 1 minute")
            return translate("util", "about {} minutes").format(value)

        case AgeUnit.HOUR:
            if value == 1:
                return translate("util", "about 1 hour")
            return translate("util", "about {} hours").format(value)

        case AgeUnit.DAY:
            if value == 1:
                return translate("util", "about 1 day")
            return translate("util", "about {} days").format(value)

        case AgeUnit.MONTH:
            if value == 1:
                return translate("util", "about 1 month")
            return translate("util", "about {} months").format(value)

        case AgeUnit.YEAR:
            if value == 1:
                return translate("util", "about 1 year")
            if distance.over:
                return translate("util", "over {} years").format(value)
            return translate("util", "about {} years").format(value)

    raise AssertionError("Unhandled age unit")


def _render_past_age(distance: AgeDistance) -> str:
    value = distance.value

    match distance.unit:
        case AgeUnit.SECOND:
            if value == 1:
                return translate("util", "1 second ago")
            return translate("util", "{} seconds ago").format(value)

        case AgeUnit.MINUTE:
            if value == 1:
                return translate("util", "about 1 minute ago")
            return translate("util", "about {} minutes ago").format(value)

        case AgeUnit.HOUR:
            if value == 1:
                return translate("util", "about 1 hour ago")
            return translate("util", "about {} hours ago").format(value)

        case AgeUnit.DAY:
            if value == 1:
                return translate("util", "about 1 day ago")
            return translate("util", "about {} days ago").format(value)

        case AgeUnit.MONTH:
            if value == 1:
                return translate("util", "about 1 month ago")
            return translate("util", "about {} months ago").format(value)

        case AgeUnit.YEAR:
            if value == 1:
                return translate("util", "about 1 year ago")
            if distance.over:
                return translate("util", "over {} years ago").format(value)
            return translate("util", "about {} years ago").format(value)

    raise AssertionError("Unhandled age unit")


def _render_future_age(distance: AgeDistance) -> str:
    value = distance.value

    match distance.unit:
        case AgeUnit.SECOND:
            if value == 1:
                return translate("util", "in 1 second")
            return translate("util", "in {} seconds").format(value)

        case AgeUnit.MINUTE:
            if value == 1:
                return translate("util", "in about 1 minute")
            return translate("util", "in about {} minutes").format(value)

        case AgeUnit.HOUR:
            if value == 1:
                return translate("util", "in about 1 hour")
            return translate("util", "in about {} hours").format(value)

        case AgeUnit.DAY:
            if value == 1:
                return translate("util", "in about 1 day")
            return translate("util", "in about {} days").format(value)

        case AgeUnit.MONTH:
            if value == 1:
                return translate("util", "in about 1 month")
            return translate("util", "in about {} months").format(value)

        case AgeUnit.YEAR:
            if value == 1:
                return translate("util", "in about 1 year")
            if distance.over:
                return translate("util", "in over {} years").format(value)
            return translate("util", "in about {} years").format(value)

    raise AssertionError("Unhandled age unit")

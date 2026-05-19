from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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
    target: datetime | timedelta,
    *,
    style: AgeStyle = AgeStyle.RELATIVE,
    include_seconds: bool = False,
) -> str:
    """Return a localized, human-readable approximate age.

    Args:
        target:
            Either:

            - datetime:
                A moment to describe relative to now.

            - timedelta:
                A direct duration to describe.
                Negative timedeltas are rendered as past.
                Positive timedeltas are rendered as future.

        style:
            AgeStyle.RELATIVE:
                "about 3 days ago"
                "in about 3 days"

            AgeStyle.PLAIN:
                "about 3 days"

        include_seconds:
            Whether values under one minute should be rendered as seconds.
    """
    delta = _target_to_delta(target)
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


def _target_to_delta(target: datetime | timedelta) -> timedelta:
    if isinstance(target, timedelta):
        return target

    return target - datetime.now(target.tzinfo)


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

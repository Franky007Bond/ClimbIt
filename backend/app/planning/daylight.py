from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from zoneinfo import ZoneInfo

from app.domain.route import Route
from app.planning.versions import SAFETY_BUFFER_MINUTES
from app.planning.versions import SAFETY_BUFFER_RULES_VERSION


@dataclass(frozen=True, slots=True)
class DaylightWindow:
    latest_safe_start_local: time | None
    be_off_by_local: time | None
    buffer_minutes: int
    rules_version: str
    explanation: list[str]


def trailhead_timezone(route: Route) -> str:
    country = route.region.country
    if country == "FR":
        return "Europe/Paris"
    if country == "DE":
        return "Europe/Berlin"
    if country == "CH":
        return "Europe/Zurich"
    if country == "AT":
        return "Europe/Vienna"
    return "UTC"


def _sunrise_sunset_utc(plan_date: date, latitude: float, longitude: float) -> tuple[datetime, datetime]:
    """NOAA-style approximate solar times (UTC)."""
    day_of_year = plan_date.timetuple().tm_yday
    lng_hour = longitude / 15.0
    zenith = math.radians(90.833)

    def _calc(is_sunrise: bool) -> datetime:
        t = day_of_year + ((6 - lng_hour) / 24 if is_sunrise else (18 - lng_hour) / 24)
        m = (0.9856 * t) - 3.289
        l = m + (1.916 * math.sin(math.radians(m))) + (0.020 * math.sin(math.radians(2 * m))) + 282.634
        l = (l + 360) % 360
        ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(l))))
        ra = (ra + 360) % 360
        l_quadrant = (math.floor(l / 90)) * 90
        ra_quadrant = (math.floor(ra / 90)) * 90
        ra = ra + (l_quadrant - ra_quadrant)
        ra /= 15
        sin_dec = 0.39782 * math.sin(math.radians(l))
        cos_dec = math.cos(math.asin(sin_dec))
        cos_h = (math.cos(zenith) - (sin_dec * math.sin(math.radians(latitude)))) / (
            cos_dec * math.cos(math.radians(latitude))
        )
        cos_h = min(1.0, max(-1.0, cos_h))
        h = (360 - math.degrees(math.acos(cos_h))) if is_sunrise else math.degrees(math.acos(cos_h))
        h /= 15
        t_local = h + ra - (0.06571 * t) - 6.622
        ut = (t_local - lng_hour) % 24
        hour = int(ut)
        minute = int((ut - hour) * 60)
        second = int((((ut - hour) * 60) - minute) * 60)
        return datetime(
            plan_date.year,
            plan_date.month,
            plan_date.day,
            hour,
            minute,
            second,
            tzinfo=timezone.utc,
        )

    return _calc(True), _calc(False)


def calculate_daylight_window(
    route: Route,
    plan_date: date,
    *,
    start_time_local: time | None = None,
) -> DaylightWindow:
    explanations: list[str] = []
    if route.duration_minutes is None:
        explanations.append("Route duration is missing; daylight window not calculated.")
        return DaylightWindow(
            latest_safe_start_local=None,
            be_off_by_local=None,
            buffer_minutes=SAFETY_BUFFER_MINUTES,
            rules_version=SAFETY_BUFFER_RULES_VERSION,
            explanation=explanations,
        )
    if route.duration_is_estimated:
        explanations.append(
            "Duration is marked estimated; latest safe start and be-off-by are not provided."
        )
        return DaylightWindow(
            latest_safe_start_local=None,
            be_off_by_local=None,
            buffer_minutes=SAFETY_BUFFER_MINUTES,
            rules_version=SAFETY_BUFFER_RULES_VERSION,
            explanation=explanations,
        )
    if route.trailhead is None:
        explanations.append("Trailhead coordinates missing; daylight window not calculated.")
        return DaylightWindow(
            latest_safe_start_local=None,
            be_off_by_local=None,
            buffer_minutes=SAFETY_BUFFER_MINUTES,
            rules_version=SAFETY_BUFFER_RULES_VERSION,
            explanation=explanations,
        )
    tz = ZoneInfo(trailhead_timezone(route))
    sunrise_utc, sunset_utc = _sunrise_sunset_utc(
        plan_date, route.trailhead.latitude, route.trailhead.longitude
    )
    sunset_local = sunset_utc.astimezone(tz)
    total_minutes = route.duration_minutes + SAFETY_BUFFER_MINUTES
    be_off_dt = sunset_local - timedelta(minutes=SAFETY_BUFFER_MINUTES)
    latest_start_dt = be_off_dt - timedelta(minutes=route.duration_minutes)
    if start_time_local is not None:
        explanations.append(f"Requested start time {start_time_local.isoformat()} noted.")
    explanations.append(
        f"Applied {SAFETY_BUFFER_MINUTES} minute safety buffer ({SAFETY_BUFFER_RULES_VERSION})."
    )
    return DaylightWindow(
        latest_safe_start_local=latest_start_dt.time().replace(second=0, microsecond=0),
        be_off_by_local=be_off_dt.time().replace(second=0, microsecond=0),
        buffer_minutes=SAFETY_BUFFER_MINUTES,
        rules_version=SAFETY_BUFFER_RULES_VERSION,
        explanation=explanations,
    )

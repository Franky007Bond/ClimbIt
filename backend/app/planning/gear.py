from __future__ import annotations

from dataclasses import dataclass

from app.domain.route import Route
from app.domain.route import RouteType
from app.planning.versions import GEAR_RULES_VERSION
from app.planning.weather import WeatherForecast


@dataclass(frozen=True, slots=True)
class GearItem:
    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class GearGuidance:
    rules_version: str
    items: list[GearItem]


def build_gear_guidance(route: Route, forecast: WeatherForecast | None) -> GearGuidance:
    items: list[GearItem] = []
    if route.route_type is RouteType.KLETTERSTEIG:
        items.extend(
            [
                GearItem(name="Harness", reason="Required base kit for Klettersteig."),
                GearItem(name="Helmet", reason="Required base kit for Klettersteig."),
                GearItem(
                    name="Via ferrata set",
                    reason="Required base kit for Klettersteig.",
                ),
            ]
        )
        if forecast is not None and forecast.temperature_c <= 5:
            items.append(
                GearItem(name="Gloves", reason="Forecast temperature at or below 5 °C.")
            )
    elif route.route_type is RouteType.ALPINE_HIKE:
        items.extend(
            [
                GearItem(name="Sturdy hiking boots", reason="Alpine hike baseline."),
                GearItem(
                    name="Water and food",
                    reason="Route duration requires self-sufficiency.",
                ),
            ]
        )
        if forecast is not None and forecast.precipitation_mm >= 1:
            items.append(
                GearItem(
                    name="Waterproof shell",
                    reason="Forecast precipitation on the route.",
                )
            )
    else:
        items.extend(
            [
                GearItem(
                    name="Approach plan",
                    reason="Climbing routes receive general approach and planning reminders only.",
                ),
                GearItem(
                    name="Weather-aware clothing",
                    reason="Check conditions before committing to the approach.",
                ),
            ]
        )
    return GearGuidance(rules_version=GEAR_RULES_VERSION, items=items)

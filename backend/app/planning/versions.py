"""Versioned planning configuration identifiers (change with tests, not ad hoc edits)."""

PLANNING_RULES_VERSION = "plan-rules-2026.10.1"
THUNDERSTORM_HEURISTIC_VERSION = "thunderstorm-heuristic-2026.10.1"
GEAR_RULES_VERSION = "gear-rules-2026.10.1"
SAFETY_BUFFER_RULES_VERSION = "safety-buffer-2026.10.1"
MOCK_WEATHER_ADAPTER_VERSION = "mock-weather-1"
MOCK_TRANSIT_ADAPTER_VERSION = "mock-transit-1"
TRANSITOUS_ADAPTER_VERSION = "transitous-1"
TRANSIT_HUB_CATALOG_VERSION = "transit-hubs-2026.10.1"

DEFAULT_DIFFICULTY_MAPPING_VERSION = "difficulty-map-2026.10.1"

WEATHER_MAX_AGE_SECONDS = 6 * 3600

# Shared buffer for daylight planning and last-return transit departure (finish + buffer).
SAFETY_BUFFER_MINUTES = 60

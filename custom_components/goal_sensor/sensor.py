"""Goal Sensor."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import requests
import json
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers import config_validation as cv, entity_platform

from .const import (
    # States
    DISABLED,
    BACK_OFF,
    IDLE,
    NO_SIGNAL,
    ACTIVE,
    GOAL,
    # Config Values
    SCORE_URL,
    TEAM,
    TIME_UNTIL_IDLE,
    IDLE_SCAN_INTERVAL,
    SCORE_RESET_TIME,
    SCORE_REQUEST_TIMEOUT,
    MAX_BACKOFF,
)

SCAN_INTERVAL = timedelta(seconds=1)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(SCORE_URL): cv.string,
        vol.Required(TEAM): cv.string,
        vol.Optional(TIME_UNTIL_IDLE): cv.positive_int,
        vol.Optional(IDLE_SCAN_INTERVAL): cv.positive_int,
        vol.Optional(SCORE_RESET_TIME): cv.positive_int,
        vol.Optional(SCORE_REQUEST_TIMEOUT): cv.positive_float,
        vol.Optional(MAX_BACKOFF): cv.positive_int,
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Goal Sensor platform."""

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("enable", {}, "enable")
    platform.async_register_entity_service("disable", {}, "disable")

    sensor = GoalSensor(
        score_url=config[SCORE_URL],
        score_request_timeout=config.get(SCORE_REQUEST_TIMEOUT, 0.5),
        team=config[TEAM].lower(),
        time_until_idle=config.get(TIME_UNTIL_IDLE, 15),
        idle_scan_interval=config.get(IDLE_SCAN_INTERVAL, 10),
        score_reset=config.get(SCORE_RESET_TIME, 1800),
        max_backoff=config.get(MAX_BACKOFF, 128),
    )
    async_add_entities([sensor], True)


class GoalSensor(SensorEntity):
    """A Goal Sensor entity."""

    _attr_name = "Goal"
    _attr_unique_id = "goal_sensor"

    def __init__(
        self,
        score_url: str,
        score_request_timeout: float,
        team: str,
        time_until_idle: int,
        idle_scan_interval: int,
        score_reset: int,
        max_backoff: int,
    ) -> None:
        """init."""
        super().__init__()

        self._attr_has_entity_name = True
        self._attr_name = "Goal"
        self._attr_native_value = IDLE

        self._score_url = score_url
        self._score_request_timeout = score_request_timeout
        self._team = team
        self._time_until_idle = time_until_idle
        self._idle_scan_interval = idle_scan_interval
        self._score_reset = score_reset
        self._max_backoff = max_backoff

        self._current_score = 0
        self._now = datetime.min
        self._last_update = datetime.min
        self._last_score = datetime.min
        self._back_off_time = datetime.min
        self._back_off = 1
        self._last_response = ""
        self._request_count = 0

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            "back_off": self._back_off,
            "score": self._current_score,
            "request_count": self._request_count,
            "last_response": self._last_response
        }

    def enable(self) -> None:
        """Enable sensor."""
        _LOGGER.info("Enabling sensor")
        self._attr_native_value = IDLE
        self._current_score = 0
        self._last_update = datetime.min
        self._last_score = datetime.min
        self._back_off_time = datetime.min
        self._back_off = 1

    def disable(self) -> None:
        """Disable sensor."""
        _LOGGER.info("Disabling sensor")
        self._attr_native_value = DISABLED

    def update(self) -> None:
        """Update the Goal Sensor entity."""
        state = self._attr_native_value

        if state == DISABLED:
            return

        self._now = datetime.today()

        if state == BACK_OFF:
            self._update_backoff_state()
        elif (
            state == IDLE or state == NO_SIGNAL
        ):  # Same logic for idle and no_signal states
            self._update_idle_state()
        elif state == ACTIVE:
            self._update_active_state()
        elif state == GOAL:
            self._update_goal_state()

    def _update_backoff_state(self) -> None:
        if self._now >= self._back_off_time:
            self._attr_native_value = IDLE
            self._last_update = datetime.min

    def _update_idle_state(self) -> None:
        # Skip updating if were idle and not enough time has passed (10 seconds by default)
        if self._time_since(self._last_update) <= self._idle_scan_interval:
            return

        # Reset the current score after the game is over (default 30 minutes)
        if (
            self._current_score > 0
            and self._time_since(self._last_score) >= self._score_reset
        ):
            _LOGGER.debug("Clearing score")
            self._current_score = 0
            return

        team_score = self._fetch_team_score()
        if team_score is None:
            return

        # Enter ACTIVE state when we first get a score or we're back at the
        # same or a higher score than we've previously seen
        if team_score >= self._current_score:
            _LOGGER.debug("Entering ACTIVE state")
            self._current_score = team_score
            self._attr_native_value = ACTIVE

    def _update_active_state(self) -> None:
        # If we haven't gotten a score in some time (default 20 minutes) set
        # the state back to idle to increase time between polling
        if self._time_since(self._last_score) >= self._time_until_idle:
            _LOGGER.debug("Going back to idle")
            self._attr_native_value = IDLE
            return

        team_score = self._fetch_team_score()
        if team_score is None:
            return

        # Scored a goal!
        if team_score > self._current_score:
            _LOGGER.debug("Goal!")
            self._attr_native_value = GOAL
            self._current_score = team_score

    def _update_goal_state(self) -> None:
        _LOGGER.debug("Clearing goal state")
        self._attr_native_value = ACTIVE

    def _increase_back_off(self) -> None:
        self._attr_native_value = BACK_OFF
        self._back_off = min(self._back_off * 2, self._max_backoff)
        self._back_off_time = self._now + timedelta(seconds=self._back_off)
        _LOGGER.warning(
            "Failed to fetch score, backing off for %s seconds until %s",
            self._back_off,
            self._back_off_time,
        )

    def _fetch_team_score(self) -> dict:
        result = self._request_score()
        _LOGGER.debug("Fetched result: '%s'", result)

        if result is None:
            return None

        self._last_response = json.dumps(result)

        self._back_off = 1
        self._last_update = self._now

        has_signal = result["hasSignal"]
        if not has_signal:
            self._attr_native_value = NO_SIGNAL
            return None

        if self._attr_native_value == NO_SIGNAL:
            self._attr_native_value = IDLE

        score = result["score"]
        team_score = score.get(self._team, None)
        if team_score is None:
            return None

        self._last_score = self._now

        return team_score

    def _request_score(self) -> dict:
        self._request_count += 1
        try:
            response = requests.get(
                self._score_url, timeout=self._score_request_timeout
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self._increase_back_off()
            return None

        try:
            response_json = response.json()
        except requests.exceptions.JSONDecodeError:
            self._increase_back_off()
            _LOGGER.warning("Did not get a json response: %s", response.content)
            return None

        if "score" not in response_json or "hasSignal" not in response_json:
            self._increase_back_off()
            _LOGGER.error("Invalid json response %s", response_json)
            return None

        return response_json

    def _time_since(self, time):
        return (self._now - time).seconds

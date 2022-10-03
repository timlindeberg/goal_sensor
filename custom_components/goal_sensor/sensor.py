"""Goal Sensor."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.helpers.config_validation as cv

from .const import (
    # States
    ACTIVE,
    GOAL,
    IDLE,
    BACK_OFF,
    # Config Values
    SCORE_URL,
    TEAM,
    TIME_UNTIL_IDLE,
    IDLE_SCAN_INTERVAL,
    SCORE_RESET_TIME,
    SCORE_REQUEST_TIMEOUT,
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(SCORE_URL): cv.string,
        vol.Required(TEAM): cv.string,
        vol.Optional(TIME_UNTIL_IDLE): cv.positive_int,
        vol.Optional(IDLE_SCAN_INTERVAL): cv.positive_int,
        vol.Optional(SCORE_RESET_TIME): cv.positive_int,
        vol.Optional(SCORE_REQUEST_TIMEOUT): cv.positive_float,
    }
)

SCAN_INTERVAL = timedelta(seconds=1)

_LOGGER = logging.getLogger(__name__)


MAX_BACKOFF = 128


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Goal Sensor platform."""
    sensor = GoalSensor(
        score_url=config[SCORE_URL],
        score_request_timeout=config.get(SCORE_REQUEST_TIMEOUT, 0.5),
        team=config[TEAM].lower(),
        time_until_idle=config.get(TIME_UNTIL_IDLE, 1200),
        idle_scan_interval=config.get(IDLE_SCAN_INTERVAL, 10),
        score_reset=config.get(SCORE_RESET_TIME, 10),
    )
    add_entities([sensor], True)


class GoalSensor(SensorEntity):
    """A Goal Sensor entity."""

    _attr_name = "Goal"

    def __init__(
        self,
        score_url: str,
        score_request_timeout: float,
        team: str,
        time_until_idle: int,
        idle_scan_interval: int,
        score_reset: int,
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

        self._current_score = None
        self._last_update = datetime.min
        self._last_score = datetime.min
        self._back_off = 1
        self._back_off_time = datetime.min

    def update(self) -> None:
        """Update the Goal Sensor entity."""
        state = self._attr_native_value
        now = datetime.today()

        if state == BACK_OFF and self._back_off_time >= now:
            return

        if state == BACK_OFF:
            # End of back off, set state to IDLE
            self._attr_native_value = IDLE

        if state == GOAL:
            _LOGGER.debug("Clearing goal state")
            self._attr_native_value = ACTIVE
            return

        # If we haven't gotten a score in some time (default 20 minutes) set
        # the state back to idle to increase time between polling
        if state is ACTIVE and (now - self._last_score).seconds > self._time_until_idle:
            _LOGGER.debug("Going back to idle")
            self._attr_native_value = IDLE
            return

        # Clear score if we don't get a new score in some time (default 10 seconds) to avoid
        # triggering the goal sensor when coming back to a match later on
        if (
            state is ACTIVE
            and self._current_score is not None
            and (now - self._last_score).seconds > self._score_reset
        ):
            _LOGGER.debug("Clearing score")
            self._current_score = None
            return

        # Skip updating if were idle and not enough time has passed (10 seconds by default)
        time_since_update = (now - self._last_update).seconds
        if state is IDLE and time_since_update <= self._idle_scan_interval:
            return

        score = self._fetch_score()
        if score is None:
            return

        self._last_update = now
        _LOGGER.debug("Fetched score: '%s'", score)

        team_score = score.get(self._team, None)
        if team_score is None:
            return

        _LOGGER.debug("Got score: %s", team_score)

        self._last_score = now
        self._attr_native_value = ACTIVE

        # Scored a goal!
        if self._current_score is not None and team_score == self._current_score + 1:
            _LOGGER.debug("Goal!")
            self._attr_native_value = GOAL

        self._current_score = team_score

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            "back_off": self._back_off,
            "score": self._current_score,
        }

    def _fetch_score(self) -> dict:
        try:
            response = requests.get(
                self._score_url, timeout=self._score_request_timeout
            ).json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self._attr_native_value = BACK_OFF
            self._back_off = min(self._back_off * 2, MAX_BACKOFF)
            self._back_off_time = datetime.today() + timedelta(seconds=self._back_off)
            _LOGGER.warning(
                "Connection timed out, backing off for %s seconds until %s",
                self._back_off,
                self._back_off_time,
            )
            return None

        _LOGGER.debug("Response: %s", response)

        if "score" not in response:
            _LOGGER.error("Invalid json response, missing 'score' field")
            return None

        return response["score"]

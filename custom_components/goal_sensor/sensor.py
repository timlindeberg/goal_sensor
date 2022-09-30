"""Goal Sensor."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ACTIVE,
    GOAL,
    IDLE,
    IDLE_SCAN_INTERVAL,
    IDLE_TIME,
    SCORE_RESET_TIME,
    TEAM,
    URL,
)
from .score_api import ScoreApi

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(URL): cv.string,
        vol.Required(TEAM): cv.string,
        vol.Optional(IDLE_TIME): cv.positive_int,
        vol.Optional(IDLE_SCAN_INTERVAL): cv.positive_int,
        vol.Optional(SCORE_RESET_TIME): cv.positive_int,
    }
)

SCAN_INTERVAL = timedelta(seconds=1)

_LOGGER = logging.getLogger(__name__)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Goal Sensor platform."""
    url = config[URL]
    team = config[TEAM].lower()

    idle_time = config.get(IDLE_TIME, 1200)  # 20 minutes
    idle_scan_interval = config.get(IDLE_SCAN_INTERVAL, 10)
    score_reset = config.get(SCORE_RESET_TIME, 10)

    sensor = GoalSensor(
        ScoreApi(url, SCAN_INTERVAL.total_seconds()),
        team,
        idle_time,
        idle_scan_interval,
        score_reset,
    )
    add_entities([sensor], True)


class GoalSensor(SensorEntity):
    """A Goal Sensor entity."""

    _attr_name = "Goal"
    _attr_native_value = IDLE

    def __init__(
        self,
        api: ScoreApi,
        team: str,
        idle_time: int,
        idle_scan_interval: int,
        score_reset: int,
    ) -> None:
        """init."""
        super().__init__()
        self._api = api
        self._team = team
        self._idle_time = idle_time
        self._idle_scan_interval = idle_scan_interval
        self._score_reset = score_reset

        self._current_score = None
        self._last_update = datetime.min
        self._last_score = datetime.min

    def update(self) -> None:
        """Update the Goal Sensor entity."""

        state = self._attr_native_value
        if state == GOAL:
            _LOGGER.debug("Clearing goal state")
            self._attr_native_value = ACTIVE
            return

        now = datetime.today()

        # If we haven't gotten a score in some time (default 20 minutes) set
        # the state back to idle to increase time between polling
        if state is ACTIVE and (now - self._last_score).seconds > self._idle_time:
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

        score = self._api.fetch_scores()
        _LOGGER.debug("Fetched score: '%s'", score)
        self._last_update = now

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

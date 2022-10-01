"""Score API."""
from __future__ import annotations

import base64
import logging
import re

import numpy as np
import pytesseract
import requests
import sys
import io

from PIL import Image, ImageEnhance, ImageMath

_LOGGER = logging.getLogger(__name__)


class ScoreApi:
    """Score API."""

    def __init__(self, url: str, timeout_seconds: float) -> None:
        """init."""
        self._url = url
        self._timeout = timeout_seconds
        self._body = '{ "command":"cropped-image" }'
        self._score = 0
        self._previous_image = ""
        self._previous_score: dict = {}
        self._score_regex = r"([A-Za-z]+).+?([0-9oOQ])-([0-9oOQ]).+?([A-Za-z]+)"

    def fetch_scores(self) -> dict:
        """Fetch scores."""

        try:
            response = requests.post(
                self._url, data=self._body, timeout=self._timeout
            ).json()
        except requests.exceptions.MissingSchema:
            _LOGGER.error(
                "Missing resource or schema in configuration. Add http:// to your URL"
            )
            return {}
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Connection timed out")
            return {}

        _LOGGER.debug("Response: %s", response)

        if "timestamp" not in response:
            _LOGGER.error("Invalid json response, missing 'timestamp' field")
            return {}

        if "image" not in response:
            _LOGGER.error("Invalid json response, missing 'image' field")
            return {}

        timestamp = datetime.utcfromtimestamp(response["timestamp"] / 1000)
        if (datetime.today() - timestamp).seconds >= 5:
            _LOGGER.debug("Image is older than 5 seconds, skipping")
            return {}

        image_text = response["image"]
        if image_text == self._previous_image:
            _LOGGER.debug("Same image as before, returning cached value")
            return self._previous_score

        self._previous_image = image_text

        image_data = base64.b64decode(image_text)

        score = self._get_score(image_data)
        self._previous_score = score
        return score

    def _get_score(self, image_data):
        image = self._process_image(image_data)
        text = self._read_text(image)
        _LOGGER.debug("Got text from image: '%s'", text)

        if len(text) == 0:
            _LOGGER.debug("Skipping image")
            return {}

        score = self._parse_score(text)
        if not score:
            return {}
        return score

    def _process_image(self, image_data):
        stream_str = io.BytesIO(image_data)
        with Image.open(stream_str) as img:
            # Turn black and white
            img = img.convert('L')

            height = img.height
            width = img.width

            # Invert the middle of the image
            start = int(0.31 * width)
            end = int(0.71 * width)
            img_array = np.array(img)
            img_slice = img_array[:, start:end] 
            img_array[:, start:end] = 255 - img_slice
            img = Image.fromarray(img_array)
            
            # Scale up
            scale = 4
            return img.resize((int(width * scale), int(height * scale)), Image.Resampling.BICUBIC)

    def _read_text(self, img):
        text = pytesseract.image_to_string(img)
        return text.replace("+", "").replace("#", "").replace("\n", " ")

    def _parse_score(self, text):
        def get_score(text):
            text = text.replace("o", "0")
            text = text.replace("O", "0")
            text = text.replace("Q", "0")
            text = text.replace("I", "1")
            text = text.replace("l", "1")
            return int(text)

        match = re.search(self._score_regex, text)
        if match is None:
            return None

        team1 = match[1].lower()
        score1 = get_score(match[2])
        score2 = get_score(match[3])
        team2 = match[4].lower()

        return {team1: score1, team2: score2}

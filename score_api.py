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
import cv2

_LOGGER = logging.getLogger(__name__)


class ScoreApi:
    """Score API."""

    def __init__(self, url: str, timeout_seconds: float) -> None:
        """init."""
        self._url = url
        self._timeout = timeout_seconds
        self._body = '{ "command":"cropped-image" }'
        self._mask = np.zeros(0)
        self._score = 0
        self._previous_image = ""
        self._previous_score: dict = {}
        self._score_regex = r"([A-Za-z]+).+?([0-9oOQ])-([0-9oOQ]).+?([A-Za-z]+)"

    def fetch_score(self) -> dict:
        """Fetch score."""

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

        if "image" not in response:
            _LOGGER.error("Invalid json response, missing 'image' field")
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
            return {}

        score = self._parse_score(text)
        if not score:
            return {}
        return score

    def _process_image(self, image_data):
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        height = img.shape[0]
        width = img.shape[1]

        if len(self._mask) != height or len(self._mask[0]) != width:
            self._mask = np.zeros((height, width, 1), np.uint8)
            self._mask[:, 0 : int(0.31 * width)] = 255
            self._mask[:, int(0.71 * width) : width] = 255

        # Black and white
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Invert edges of the image (part that has the team names, the middle already has the correct colors)
        img = cv2.bitwise_not(img, img, mask=self._mask)

        # Scale up
        scale = 4.0  # percent of original size
        dim = (int(img.shape[1] * scale), int(img.shape[0] * scale))
        return cv2.resize(img, dim, interpolation=cv2.INTER_CUBIC)

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

if __name__ == '__main__':
    url = sys.argv[1]
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    _LOGGER.addHandler(ch)
    _LOGGER.setLevel(logging.DEBUG)
    
    api = ScoreApi(url, 5)
    scores = api.fetch_scores()
    print(f"Scores: {scores}")

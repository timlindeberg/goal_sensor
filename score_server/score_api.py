import base64
import logging
import re

import numpy as np
import pytesseract
import requests
import cv2
import argparse
from extract_score import ScoreExtractor

_LOGGER = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Extract score from a fetched image')
    parser.add_argument('url', type=str, help='The url where the image should be fetched')
    parser.add_argument('--save_images', action='store_true', help='If specified, the images are saved')
    parser.add_argument('--tesseract_path', type=str, default=None, help='Path to the tesseract executable')
    parser.add_argument('--no_signal_image', type=str, default=None, help='Path to a image that is shown when there is no signal')
    return parser.parse_args()


class ScoreApi:
    """Score API."""

    def __init__(self, url: str, timeout_seconds: float, score_extractor: ScoreExtractor) -> None:
        """init."""
        self._url = url
        self._timeout = timeout_seconds
        self._score_extractor = score_extractor

        self._body = '{ "command":"cropped-image" }'
        self._previous_image = ""
        self._previous_score: dict = {}

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

        score = self._score_extractor.get_score(image_data)
        self._previous_score = score 
        return score

if __name__ == '__main__':
    args = parse_args()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    _LOGGER.addHandler(ch)
    _LOGGER.setLevel(logging.DEBUG)
    
    score_extractor = ScoreExtractor(args.save_images, args.tesseract_path, args.no_signal_image)
    api = ScoreApi(args.url, 5, score_extractor)
    scores = api.fetch_score()
    print(f"Scores: {scores}")

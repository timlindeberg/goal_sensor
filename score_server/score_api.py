import base64
import requests
import argparse
import logging

from score_reader import ScoreReader
from signal_checker import SignalChecker
from score_readers.score_readers import SCORE_READERS
from utils import setup_logger, image_from_buffer


_LOGGER = logging.getLogger(__name__)


class ScoreApi:
    """Score API."""

    def __init__(self, url: str, timeout_seconds: float, score_reader: ScoreReader, signal_checker: SignalChecker) -> None:
        """init."""
        self._url = url
        self._timeout = timeout_seconds
        self._signal_checker = signal_checker
        self._score_reader = score_reader

        self._body = '{ "command":"cropped-image" }'
        self._previous_image = ""
        self._previous_score: dict = {}

    def fetch_score(self) -> dict:
        """Fetch score."""

        image_text = self._request_image_data()

        if image_text == self._previous_image:
            _LOGGER.debug("Same image as before, returning cached score")
            return self._previous_score

        img = self._get_image(image_text)
        score = self._score_reader.read_score(img)

        self._previous_image = image_text
        self._previous_score = score
        return score

    def has_signal(self) -> bool:
        """Check signal."""
        image_text = self._request_image_data()
        img = self._get_image(image_text)
        return self._signal_checker.has_signal(img)

    def _get_image(self, image_text):
        image_data = base64.b64decode(image_text)
        return image_from_buffer(image_data)

    def _request_image_data(self) -> str:
        try:
            response = requests.post(
                self._url, data=self._body, timeout=self._timeout
            ).json()
        except requests.exceptions.MissingSchema:
            _LOGGER.error(
                "Missing resource or schema in configuration. Add http:// to your URL"
            )
            return None
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Connection timed out")
            return None

        _LOGGER.debug("Response: %s", response)

        if "image" not in response:
            _LOGGER.error("Invalid json response, missing 'image' field")
            return None

        return response["image"]


def parse_args():
    parser = argparse.ArgumentParser(description='Extract score from a fetched image')
    parser.add_argument('url', type=str, help='The url where the image should be fetched')
    parser.add_argument('--score_reader', type=str, choices=SCORE_READERS.keys(), help='Which score reader to use')
    parser.add_argument('--save_images', action='store_true', help='If specified, the images are saved')
    parser.add_argument('--tesseract_path', type=str, default=None, help='Path to the tesseract executable')
    parser.add_argument('--no_signal_image', type=str, default=None, help='Path to a image that is shown when there is no signal')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    setup_logger()

    score_reader = SCORE_READERS[args.score_reader](args.save_images, args.tesseract_path)
    signal_checker = SignalChecker(args.no_signal_image)
    api = ScoreApi(args.url, 5, score_reader, signal_checker)
    
    scores = api.fetch_score()
    print(f"Scores: {scores}")

    has_signal = api.has_signal()
    print(f"Has signal: {has_signal}")

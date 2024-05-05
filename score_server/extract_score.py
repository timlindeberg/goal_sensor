import logging
import re

import numpy as np
import pytesseract
import cv2
import argparse
from pathlib import Path
from score_reader import ScoreReader
from score_readers.score_readers import SCORE_READERS


_LOGGER = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Extract score from an image')
    parser.add_argument('image', type=str, help='The image to extract from')
    parser.add_argument('--score_reader', type=str, choices=SCORE_READERS.keys(), help='Which score reader to use')
    parser.add_argument('--save_images', action='store_true', help='If specified, the images are saved')
    parser.add_argument('--tesseract_path', type=str, default=None, help='Path to the tesseract executable')
    parser.add_argument('--no_signal_image', type=str, default=None, help='Path to a image that is shown when there is no signal')
    return parser.parse_args()

class ScoreExtractor:

    def __init__(self, score_reader: ScoreReader, tesseract_path: str | None, no_signal_image: str | None) -> None:
        """init."""
        self._score_reader = score_reader
        if tesseract_path is not None:
            path = Path(tesseract_path).resolve()
            _LOGGER.info("Setting tesseract path to %s", path)
            pytesseract.pytesseract.tesseract_cmd = path

        self._no_signal_image = None
        if no_signal_image is not None:
            with open(no_signal_image, 'rb') as f:
                _LOGGER.info("Using no signal image %s", no_signal_image)
                self._no_signal_image = self._image_from_buffer(f.read())

    def get_score(self, image_data) -> dict:
        nparr = np.frombuffer(image_data, np.uint8)
        img = self._image_from_buffer(image_data)

        has_signal = not self._is_no_signal_image(img)
        score = self._score_reader.read_score(img) if has_signal else {}
        return { "hasSignal": has_signal, "score": score }


    def _image_from_buffer(self, image_data):
        nparr = np.frombuffer(image_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    def _is_no_signal_image(self, img):
        if self._no_signal_image is None:
            return False

        if self._no_signal_image.shape[0] != img.shape[0] or self._no_signal_image.shape[1] != img.shape[1]:
            _LOGGER.error("Image shape was different from the no signal image.")
            return False

        norm = cv2.norm(self._no_signal_image - img, cv2.NORM_L2)
        distance = norm / (img.shape[0] * img.shape[1])
        return distance <= 0.0001

if __name__ == '__main__':
    args = parse_args()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    _LOGGER.addHandler(ch)
    _LOGGER.setLevel(logging.DEBUG)


    score_reader = SCORE_READERS[args.score_reader](args.save_images)
    score_extractor = ScoreExtractor(score_reader, args.tesseract_path, args.no_signal_image)
    
    with open(args.image, 'rb') as f:
        data = f.read()
    scores = score_extractor.get_score(data)
    print(f"Scores: {scores}")

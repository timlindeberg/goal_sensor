"""Score API."""
import logging
import re

import numpy as np
import pytesseract
import cv2
import argparse
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Extract score from an image')
    parser.add_argument('image', type=str, help='The image to extract from')
    parser.add_argument('--save_images', action='store_true', help='If specified, the images are saved')
    parser.add_argument('--tesseract_path', type=str, default=None, help='Path to the tesseract executable')
    parser.add_argument('--no_signal_image', type=str, default=None, help='Path to a image that is shown when there is no signal')
    return parser.parse_args()

class ScoreExtractor:

    def __init__(self, save_images: bool, tesseract_path: str | None, no_signal_image: str | None) -> None:
        """init."""
        self._save_images = save_images

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
        score = self._calculate_score(img) if has_signal else {}
        return { "hasSignal": has_signal, "score": score }

    def _calculate_score(self, img) -> dict:
        img_left, img_middle, img_right = self._split_image(img)

        team1 = self._read_text(img_left, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVXYZ')
        team2 = self._read_text(img_right, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVXYZ')
        score_text = self._read_text(img_middle, allowed_chars='-0123456789')

        if len(team1) == 0 or len(team2) == 0 or len(score_text) == 0:
            return {}

        if '-' not in score_text:
            return {}

        scores = score_text.split('-')
        if len(scores) != 2:
            return {}

        return {team1: int(scores[0]), team2: int(scores[1])}

    def _split_image(self, img):
        self._save_image(img, "initial")

        # Black and white
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self._save_image(img, "black_white")

        width = img.shape[1]

        # Split image into three parts containing the left team name, the score and the right team name
        img_left = img[:, 0 : int(0.25 * width)]
        img_middle = img[:, int(0.35 * width) : int(0.65 * width)]
        img_right = img[:, int(0.77 * width) : width]

        self._save_image(img_left, "left")
        self._save_image(img_middle, "middle")
        self._save_image(img_right, "right")

        return img_left, img_middle, img_right

    def _save_image(self, img, name):
        if self._save_images:
            Path("./images").mkdir(exist_ok=True)
            cv2.imwrite(f"./images/{name}.jpg", img)

    def _read_text(self, img, allowed_chars):
        text = pytesseract.image_to_string(img, lang='eng', config=f'--psm 7 -c tessedit_char_whitelist={allowed_chars}')
        return text.strip().lower()

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

    score_extractor = ScoreExtractor(args.save_images, args.tesseract_path, args.no_signal_image)
    
    with open(args.image, 'rb') as f:
        data = f.read()
    scores = score_extractor.get_score(data)
    print(f"Scores: {scores}")

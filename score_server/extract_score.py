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
    return parser.parse_args()

class ScoreExtractor:

    def __init__(self, save_images=False) -> None:
        """init."""
        self._save_images = save_images

    def get_score(self, image_data):
        img_left, img_middle, img_right = self._get_images(image_data)

        team1 = self._read_text(img_left, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVXYZ')
        team2 = self._read_text(img_right, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVXYZ')
        score_text = self._read_text(img_middle, allowed_chars='-0123456789')

        return self._parse_score(team1, team2, score_text)

    def _get_images(self, image_data):
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        height = img.shape[0]
        width = img.shape[1]

        self._save_image(img, "initial")

        # Black and white
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self._save_image(img, "black_white")

        # Split image into three parts containing the left team name, the score and the right team name
        img_left = img[:, 0:int(0.25*width)]
        
        # Invert the middle image to make it black text on white background
        img_middle = img[:, int(0.35*width):int(0.65*width)]
        img_middle = cv2.bitwise_not(img_middle)

        img_right = img[:, int(0.77*width):width]

        self._save_image(img_left, "left")
        self._save_image(img_middle, "middle")
        self._save_image(img_right, "right")

        return img_left, img_middle, img_right

    def _parse_score(self, team1, team2, score_text):
        if len(team1) == 0 or len(team2) == 0 or len(score_text) == 0:
            return {}

        if '-' not in score_text:
            return {}

        scores = score_text.split('-')
        if len(scores) != 2:
            return {}

        return {team1: int(scores[0]), team2: int(scores[1])}

    def _save_image(self, img, name):
        if self._save_images:
            Path("./images").mkdir(exist_ok=True)
            cv2.imwrite(f"./images/{name}.jpg", img)

    def _read_text(self, img, allowed_chars):
        text = pytesseract.image_to_string(img, lang='eng', config=f'--psm 7 -c tessedit_char_whitelist={allowed_chars}')
        return text.strip().lower()

if __name__ == '__main__':
    args = parse_args()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    _LOGGER.addHandler(ch)
    _LOGGER.setLevel(logging.DEBUG)

    score_extractor = ScoreExtractor(args.save_images)
    
    with open(args.image, 'rb') as f:
        data = f.read()
    scores = score_extractor.get_score(data)
    print(f"Scores: {scores}")

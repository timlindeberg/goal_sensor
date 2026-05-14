import cv2
import numpy as np
import pytesseract

from score_reader import ScoreReader


class TV42026ScoreReader(ScoreReader):

    def __init__(self, save_images: bool, tesseract_path: str | None, team_name_time_out: int | None) -> None:
        super().__init__(save_images, tesseract_path, team_name_time_out)

    def read_score(self, img) -> dict:
        img_left_name, img_right_name, img_left_score, img_right_score = self._split_image(img)
        self._read_team_names(img_left_name, img_right_name)

        left_score = self._read_score_digit(img_left_score)
        right_score = self._read_score_digit(img_right_score)

        if self._team1 is None or self._team2 is None:
            return {}

        if not left_score.isdigit() or not right_score.isdigit():
            return {}

        return {self._team1: int(left_score), self._team2: int(right_score)}

    def _parse_team_name(self, img) -> str:
        # The right name image is a wider crop containing logo + name.
        # Try multiple PSM modes and return the first plausible result (>= 2 chars).
        for use_thresh in [False, True]:
            region = img
            if use_thresh:
                _, region = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
            for psm in [7, 8]:
                text = self._read_text(region, psm=psm, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                if len(text) >= 2:
                    return text
        return self._read_text(img, psm=7, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ')

    def _read_score_digit(self, img) -> str:
        return self._read_text(img, psm=8, allowed_chars='0123456789')

    def _split_image(self, img):
        self._save_image(img, "initial")

        h, w = img.shape[:2]
        scale = 6

        # Extract bright (white) pixels for score regions — scores are white text on blue background
        b, g, r = cv2.split(img)
        bright_mask = (b.astype(int) + g.astype(int) + r.astype(int)) > 500
        score_img = np.where(bright_mask[:, :, np.newaxis], img, np.zeros_like(img))
        score_big = cv2.resize(score_img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        score_inv = 255 - cv2.cvtColor(score_big, cv2.COLOR_BGR2GRAY)

        # Grayscale for team names
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        big = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        bw = w * scale

        img_left_name = big[:, 0:int(0.25 * bw)]
        # Right name crop starts wider to accommodate different logo widths
        img_right_name = big[:, int(0.73 * bw):]

        # Scores are inside the blue box: left score ~37-47%, right score ~51-65%
        img_left_score = score_inv[:, int(0.37 * bw):int(0.47 * bw)]
        img_right_score = score_inv[:, int(0.51 * bw):int(0.65 * bw)]

        self._save_image(img_left_name, "left_name")
        self._save_image(img_right_name, "right_name")
        self._save_image(img_left_score, "left_score")
        self._save_image(img_right_score, "right_score")

        return img_left_name, img_right_name, img_left_score, img_right_score

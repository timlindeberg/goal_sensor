import cv2
import numpy as np

from pathlib import Path
from utils import read_image

from score_reader import ScoreReader



class Discovery2024ScoreReader(ScoreReader):

    def __init__(self, save_images: bool, tesseract_path: str | None, team_name_time_out: int | None) -> None:
        super().__init__(save_images, tesseract_path, team_name_time_out)
        self.img_dash = self._read_dash_img()
        

    def read_score(self, img) -> dict:
        img_left, img_right, img_score = self._split_image(img)
        self._read_team_names(img_left, img_right)

        score = self._read_score(img_score)

        if self._team1 is None or self._team2 is None or len(score) != 3 or '-' not in score:
            return {}

        scores = score.split("-")

        return {self._team1: int(scores[0]), self._team2: int(scores[1])}

    def _parse_team_name(self, img) -> str:
        return self._read_text(img, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVXYZ', pattern=r'\A\A\A')

    def _read_score(self, img):
        return self._read_text(img, allowed_chars="-0123456789", pattern=r'\d-\d')

    def _split_image(self, img):
        self._save_image(img, "initial")

        # Black and white
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self._save_image(img, "black_white")

        width = img.shape[1]

        # Split image into three parts containing the left team name, the score and the right team name
        img_left_name = img[:, 0 : int(0.22 * width)]
        img_left_score = img[:, int(0.30 * width) : int(0.40 * width)]

        img_right_score = img[:, int(0.62 * width) : int(0.72 * width)]
        img_right_name = img[:, int(0.82 * width) : width]

        # Build up a in image with the score seperated by a dash (e.g. 1-2), this seems to help tesseract
        # to read the numbers
        img_score = np.concatenate((img_left_score, self.img_dash, img_right_score), axis=1)

        # Unsharp mask seems to help with reading the score but makes reading the team names worse
        img_score = self._unsharp_mask(img_score, amount=2.0)

        self._save_image(img_left_name, "left_name")
        self._save_image(img_left_score, "left_score")
        self._save_image(img_right_name, "right_name")
        self._save_image(img_right_score, "right_score")
        self._save_image(img_score, "img_score")

        return img_left_name, img_right_name, img_score

    def _unsharp_mask(self, image, kernel_size=(5, 5), sigma=1.0, amount=1.0, threshold=1):
        blurred = cv2.GaussianBlur(image, kernel_size, sigma)
        sharpened = float(amount + 1) * image - float(amount) * blurred
        sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
        sharpened = np.minimum(sharpened, 255 * np.ones(sharpened.shape))
        sharpened = sharpened.round().astype(np.uint8)
        if threshold > 0:
            low_contrast_mask = np.absolute(image - blurred) < threshold
            np.copyto(sharpened, image, where=low_contrast_mask)
        return sharpened

    def _read_dash_img(self):
        current_dir = Path(__file__).parents[0]
        img_dash_path = Path(current_dir, "dash.jpg")
        img = read_image(img_dash_path)
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

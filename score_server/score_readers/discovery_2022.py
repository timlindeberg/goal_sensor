import cv2

from score_reader import ScoreReader


class Discovery2022ScoreReader(ScoreReader):

    def __init__(self, save_images: bool, tesseract_path: str | None) -> None:
        super().__init__(save_images, tesseract_path)

    def read_score(self, img) -> dict:
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


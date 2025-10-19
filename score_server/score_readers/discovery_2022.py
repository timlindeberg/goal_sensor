import cv2

from score_reader import ScoreReader


class Discovery2022ScoreReader(ScoreReader):

    def __init__(self, save_images: bool, tesseract_path: str | None, team_name_time_out: int | None) -> None:
        super().__init__(save_images, tesseract_path, team_name_time_out)

    def read_score(self, img) -> dict:
        img_left, img_middle, img_right = self._split_image(img)

        self._read_team_names(img_left, img_right)
        score_text = self._read_text(img_middle, allowed_chars='-0123456789')

        if self._team1 is None or self._team2 is None or len(score_text) == 0:
            return {}

        if '-' not in score_text:
            return {}

        scores = score_text.split('-')
        if len(scores) != 2:
            return {}

        return {self._team1: int(scores[0]), self._team2: int(scores[1])}


    def _parse_team_name(self, img) -> str:
        return self._read_text(img, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVXYZ')

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


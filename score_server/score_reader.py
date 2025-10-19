import cv2
import pytesseract
import logging
import time

from pathlib import Path


_LOGGER = logging.getLogger(__name__)


class ScoreReader:
    def __init__(self, save_images: bool, tesseract_path: str | None, team_name_time_out: int | None) -> None:
        """init."""
        self._last_pattern = None
        self._save_images = save_images
        if tesseract_path is not None:
            path = Path(tesseract_path).resolve()
            _LOGGER.info("Setting tesseract path to %s", path)
            pytesseract.pytesseract.tesseract_cmd = path
        self._team_name_time_out = 0 if team_name_time_out is None else team_name_time_out
        self._team1 = None
        self._team2 = None
        self._last_name_calculation = time.time()

    def _save_image(self, img, name):
        if self._save_images:
            Path("./images").mkdir(exist_ok=True)
            cv2.imwrite(f"./images/{name}.jpg", img)

    def _read_team_names(self, img_left, img_right) -> str:
        now = time.time()
        time_since_last_refresh = now - self._last_name_calculation
        _LOGGER.debug("Time since last refresh: %s", time_since_last_refresh)
        if time_since_last_refresh >= self._team_name_time_out:
            self._team1 = None
            self._team2 = None

        if self._team1 is None:
            _LOGGER.debug("Recalculating team names")
            self._team1 = self._parse_team_name(img_left)
            self._team2 = self._parse_team_name(img_right)
            self._last_name_calculation = now

            if len(self._team1) == 0:
                self._team1 = None
            if len(self._team2) == 0:
                self._team2 = None

    def _parse_team_name(self, img) -> str:
        pass

    def _read_text(self, img, psm=None, allowed_chars=None, pattern=None):
        if psm == None:
            psm = 7
        config = f'--psm {psm}'
        if pattern != None:
            file_path = Path('./score.patterns')
            config += f'  --user-patterns {file_path.resolve()}'
            if pattern != self._last_pattern:
                with open(file_path, 'w') as f:
                    f.write(f'{pattern}\n\n')
                self._last_pattern = pattern

        if allowed_chars != None:
            config += f' -c tessedit_char_whitelist={allowed_chars}'

        text = pytesseract.image_to_string(img, lang='eng', config=config)
        return text.strip().lower()

    def read_score(self, img) -> dict:
        """Read score."""
        pass

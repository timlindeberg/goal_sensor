import pytesseract
import cv2
import tempfile
from pathlib import Path

class ScoreReader:
    def __init__(self, save_images: bool) -> None:
        """init."""
        self._save_images = save_images

    def _save_image(self, img, name):
        if self._save_images:
            Path("./images").mkdir(exist_ok=True)
            cv2.imwrite(f"./images/{name}.jpg", img)

    def _read_text(self, img, psm=None, allowed_chars=None, pattern=None):
        if psm == None:
            psm = 7
        config = f'--psm {psm}'
        if pattern != None:
            file_path = Path('./score.patterns')
            with open(file_path, 'w') as f:
                f.write(f'{pattern}\n\n')
            config += f'  --user-patterns {file_path.resolve()}'

        if allowed_chars != None:
            config += f' -c tessedit_char_whitelist={allowed_chars}'

        text = pytesseract.image_to_string(img, lang='eng', config=config)
        return text.strip().lower()


    def read_score(self, img) -> dict:
        pass

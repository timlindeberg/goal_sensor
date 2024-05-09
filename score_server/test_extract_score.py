import unittest

__unittest = True

from pathlib import Path
from utils import read_image

from score_readers.discovery_2022 import Discovery2022ScoreReader
from score_readers.discovery_2024 import Discovery2024ScoreReader


class TestScoreReader(unittest.TestCase):
    
    _team_substitions = {
        'var': ['uar'],
        'vsk': ['usk'],
        'vär': ['var', 'uar'],
        'göt': ['got'],
        'dif': ['oif'],
    }

    def test_discovery2022(self):
        self._test_images(Discovery2022ScoreReader, 'test_images/discovery_2022')

    def test_discovery2024(self):
        self._test_images(Discovery2024ScoreReader, 'test_images/discovery_2024')

    def _test_images(self, score_reader_type, path):
        self._score_reader = score_reader_type(save_images=False, tesseract_path=None)
        for directory in Path(path).glob('*'):
            teams = directory.name.split('_')

            for image in directory.glob('*'):
                score = [int(score) for score in image.stem.split('_')]
                expected_score = { team: score for (team, score) in zip(teams, score) }
                self._test_image(image, expected_score)
      
    def _test_image(self, image_path, expected_score):
        image = read_image(image_path)
        scores = self._score_reader.read_score(image)

        with self.subTest(msg="Checking image", image=str(image_path)):
            for team, score in expected_score.items():
                self.assertTrue(self._has_score(team, score, scores), msg=f"Expected {expected_score}, got {scores}")

    def _has_score(self, team, score, extracted_score):
        team_names = [team] + self._team_substitions.get(team, [])
        return any(extracted_score.get(alias, None) == score for alias in team_names)

if __name__ == '__main__':
    unittest.main()

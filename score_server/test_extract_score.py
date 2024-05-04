import unittest

__unittest = True

from extract_score import ScoreExtractor
from score_readers.discovery_2022 import Discovery2022ScoreReader
from score_readers.discovery_2024 import Discovery2024ScoreReader
from pathlib import Path


class TestScoreExtractor(unittest.TestCase):
    
    _team_substitions = {
        'var': ['uar'],
        'vsk': ['uar'],
        'vär': ['var', 'uar'],
        'göt': ['got'],
        'dif': ['oif'],
    }

    def test_discovery2022(self):
        self._test_images(Discovery2022ScoreReader, 'test_images/discovery_2022')

    def test_discovery2024(self):
        self._test_images(Discovery2024ScoreReader, 'test_images/discovery_2024')

    def _test_images(self, score_reader_type, path):
        self._create_score_extractor(score_reader_type)
        for directory in Path(path).glob('*'):
            teams = directory.name.split('_')

            for image in directory.glob('*'):
                score = [int(score) for score in image.stem.split('_')]
                expected_score = { team: score for (team, score) in zip(teams, score) }
                self._test_image(image, expected_score)
      
    def _test_image(self, image, expected_score):
        with open(image, 'rb') as f:
            data = f.read()

        scores = self._score_extractor.get_score(data)["score"]

        with self.subTest(msg="Checking image", image=str(image)):
            for team, score in expected_score.items():
                self.assertTrue(self._has_score(team, score, scores), msg=f"Expected {expected_score}, got {scores}")

    def _has_score(self, team, score, extracted_score):
        team_names = [team] + self._team_substitions.get(team, [])
        return any(extracted_score.get(alias, None) == score for alias in team_names)

    def _create_score_extractor(self, score_reader_type):
        score_reader = score_reader_type(save_images=False)
        self._score_extractor = ScoreExtractor(score_reader, tesseract_path=None, no_signal_image=None)

if __name__ == '__main__':
    unittest.main()

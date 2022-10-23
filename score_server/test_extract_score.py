import unittest

__unittest = True

from extract_score import ScoreExtractor
from pathlib import Path


class TestScoreExtractor(unittest.TestCase):
    
    _score_extractor = ScoreExtractor(save_images=False)

    _team_substitions = {
        'var': ['uar'],
        'vär': ['var', 'uar'],
        'göt': ['got'],
        'dif': ['oif'],
    }

    def test_images(self):
        for directory in Path('test_images').glob('*'):
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

if __name__ == '__main__':
    unittest.main()

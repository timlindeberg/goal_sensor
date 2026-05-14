from score_readers.discovery_2022 import Discovery2022ScoreReader
from score_readers.discovery_2024 import Discovery2024ScoreReader
from score_readers.tv4_2026 import TV42026ScoreReader


SCORE_READERS = {
    'discovery2022': Discovery2022ScoreReader,
    'discovery2024': Discovery2024ScoreReader,
    'tv42026': TV42026ScoreReader,
}

import argparse

from score_readers.score_readers import SCORE_READERS
from utils import read_image, setup_logger


def parse_args():
    parser = argparse.ArgumentParser(description='Read score from an image')
    parser.add_argument('image', type=str, help='The image to read from')
    parser.add_argument('--score_reader', type=str, choices=SCORE_READERS.keys(), help='Which score reader to use')
    parser.add_argument('--save_images', action='store_true', help='If specified, the images are saved')
    parser.add_argument('--tesseract_path', type=str, default=None, help='Path to the tesseract executable')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    setup_logger()

    score_reader = SCORE_READERS[args.score_reader](args.save_images, args.tesseract_path)

    image = read_image(args.image)

    scores = score_reader.read_score(image)
    print(f"Scores: {scores}")
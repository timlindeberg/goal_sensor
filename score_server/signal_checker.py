import cv2
import argparse
import logging

from utils import setup_logger, read_image


_LOGGER = logging.getLogger(__name__)


class SignalChecker:

    def __init__(self, no_signal_image: str) -> None:
        """init."""
        _LOGGER.info("Using no signal image %s", no_signal_image)
        self._no_signal_image = read_image(no_signal_image)

    def has_signal(self, img) -> bool:
        """Has signal."""

        return not self._is_no_signal_image(img)

    def _is_no_signal_image(self, img) -> bool:
        if self._no_signal_image.shape[0] != img.shape[0] or self._no_signal_image.shape[1] != img.shape[1]:
            _LOGGER.error("Image shape was different from the no signal image.")
            return False

        norm = cv2.norm(self._no_signal_image - img, cv2.NORM_L2)
        distance = norm / (img.shape[0] * img.shape[1])
        return distance <= 0.0001


def parse_args():
    parser = argparse.ArgumentParser(description='Check if theres a signal based on a cropped image')
    parser.add_argument('image', type=str, help='The image to extract from')
    parser.add_argument('--no_signal_image', type=str, help='Path to an image that is shown when there is no signal')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    setup_logger()

    signal_checker = SignalChecker(args.no_signal_image)
    
    image = read_image(args.image)

    has_signal = signal_checker.has_signal(image)
    print(f"Has signal: {has_signal}")

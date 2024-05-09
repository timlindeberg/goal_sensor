import cv2
import numpy as np
import logging
import logging.handlers
import time

from pathlib import Path


def image_from_buffer(buffer):
    nparr = np.frombuffer(buffer, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def read_image(file):
    with open(file, 'rb') as f:
        return image_from_buffer(f.read())

def setup_logger(log_level='debug', log_to_file=False):
    formatter = logging.Formatter('%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
    formatter.converter = time.gmtime # UTC time

    logger = logging.getLogger()

    if log_to_file:
        script_dir = Path(__file__).resolve().parent
        log_dir = script_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "score_server.log"
        rotating_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=32_000_00, backupCount=3)
        rotating_handler.setFormatter(formatter)
        logger.addHandler(rotating_handler)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(get_log_level(log_level))

def get_log_level(log_level):
    if log_level == 'debug':
        return logging.DEBUG
    if log_level == 'info':
        return logging.INFO
    if log_level == 'warning':
        return logging.WARNING
    return logging.ERROR
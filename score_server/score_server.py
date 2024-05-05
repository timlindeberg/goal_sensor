from score_api import ScoreApi
from extract_score import ScoreExtractor
from score_reader import ScoreReader
from score_readers.score_readers import SCORE_READERS

from http.server import BaseHTTPRequestHandler, HTTPServer

from flask import Flask
from pathlib import Path

import waitress
import sys
import logging
import logging.handlers
import time
import os
import argparse

_LOGGER = logging.getLogger(__name__)

def parse_args():
	parser = argparse.ArgumentParser(description='Run the score server')
	parser.add_argument('--url', type=str, help='The url where the image should be fetched')
	parser.add_argument('--port', type=int, help='The port to run the server at')
	parser.add_argument('--score_reader', type=str, choices=SCORE_READERS.keys(), help='Which score reader to use')
	parser.add_argument('--log_level', choices=['debug', 'info', 'warning', 'error'], type=str, default='info', help='The log level')
	parser.add_argument('--tesseract_path', type=str, default=None, help='Path to the tesseract executable')
	parser.add_argument('--no_signal_image', type=str, default=None, help='Path to a image that is shown when there is no signal')

	return parser.parse_args()

def get_log_level(log_level):
	if log_level == 'debug':
		return logging.DEBUG
	if log_level == 'info':
		return logging.INFO
	if log_level == 'warning':
		return logging.WARNING
	return logging.ERROR

def setup_logging(log_level):
	script_dir = Path(__file__).resolve().parent
	log_dir = script_dir / "logs"
	log_dir.mkdir(exist_ok=True)

	logger = logging.getLogger()

	formatter = logging.Formatter('%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
	formatter.converter = time.gmtime  # if you want UTC time

	log_file = log_dir / "score_server.log"
	rotating_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=32_000_00, backupCount=3)
	rotating_handler.setFormatter(formatter)
	logger.addHandler(rotating_handler)

	stream_handler = logging.StreamHandler()
	stream_handler.setFormatter(formatter)
	logger.addHandler(stream_handler)

	logger.setLevel(log_level)

def run_server(port, score_api):
	app = Flask(__name__)
	@app.route("/", methods=['GET'])
	def index():
		result = score_api.fetch_score()
		_LOGGER.info("Got request with response: %s", result)
		return result

	waitress.serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
	args = parse_args()
	setup_logging(get_log_level(args.log_level))

	save_images = False
	score_reader = SCORE_READERS[args.score_reader](save_images)
	score_extractor = ScoreExtractor(score_reader, args.tesseract_path, args.no_signal_image)

	timeout = 2
	api = ScoreApi(args.url, timeout, score_extractor)

	run_server(args.port, api)

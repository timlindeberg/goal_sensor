import waitress
import sys
import logging
import os
import argparse

from http.server import BaseHTTPRequestHandler, HTTPServer
from flask import Flask

from score_api import ScoreApi
from score_reader import ScoreReader
from signal_checker import SignalChecker
from score_readers.score_readers import SCORE_READERS
from utils import setup_logger


_LOGGER = logging.getLogger(__name__)

def _log_and_return(response):
	_LOGGER.info("Got request with response: %s", response)
	return response


def run_server(port, score_api):
	app = Flask(__name__)
	@app.route("/score", methods=['GET'])
	def score():
		result = score_api.fetch_score()
		return _log_and_return({ "score": result })

	@app.route("/hasSignal", methods=['GET'])
	def has_signal():
		result = score_api.has_signal()
		return _log_and_return({ "hasSignal": result })

	waitress.serve(app, host="0.0.0.0", port=port)



def parse_args():
	parser = argparse.ArgumentParser(description='Run the score server')
	parser.add_argument('--url', type=str, help='The url where the image should be fetched')
	parser.add_argument('--port', type=int, help='The port to run the server at')
	parser.add_argument('--score_reader', type=str, choices=SCORE_READERS.keys(), help='Which score reader to use')
	parser.add_argument('--log_level', choices=['debug', 'info', 'warning', 'error'], type=str, default='info', help='The log level')
	parser.add_argument('--no_signal_image', type=str, help='Path to a image that is shown when there is no signal')
	parser.add_argument('--tesseract_path', type=str, default=None, help='Path to the tesseract executable')

	return parser.parse_args()

if __name__ == "__main__":
	args = parse_args()
	setup_logger(log_level=args.log_level, log_to_file=True)

	save_images = False
	score_reader = SCORE_READERS[args.score_reader](save_images, args.tesseract_path)
	signal_checker = SignalChecker(args.no_signal_image)

	timeout = 2
	api = ScoreApi(args.url, timeout, score_reader, signal_checker)

	run_server(args.port, api)

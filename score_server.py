from score_api import ScoreApi
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
	parser.add_argument('--loglevel', choices=['debug', 'info', 'warning', 'error'], type=str, default='info', help='The log level')

	return parser.parse_args()

def get_log_level(log_level):
	if loglevel == 'debug':
		return logging.DEBUG
	if loglevel == 'info':
		return logging.INFO
	if loglevel == 'warning':
		return logging.WARNING
	return logging.ERROR

def setup_logging(log_level):
	Path("./logs").mkdir(exist_ok=True)

	logger = logging.getLogger()

	formatter = logging.Formatter('%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
	formatter.converter = time.gmtime  # if you want UTC time

	rotating_handler = logging.handlers.RotatingFileHandler('logs/score_server.log', maxBytes=32_000_00, backupCount=3)
	rotating_handler.setFormatter(formatter)
	logger.addHandler(rotating_handler)

	stream_handler = logging.StreamHandler()
	stream_handler.setFormatter(formatter)
	logger.addHandler(stream_handler)

	logger.setLevel(log_level)

def run_server(image_url, port):
	app = Flask(__name__)
	api = ScoreApi(image_url, 2)

	@app.route("/", methods=['GET'])
	def index():
		score = api.fetch_score()
		_LOGGER.info("Got request with response: %s", score)
		return { "score": score }

	waitress.serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
	args = parse_args()
	setup_logging(get_log_level(args.loglevel))
	run_server(args.url, args.port)

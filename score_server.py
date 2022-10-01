from score_api import ScoreApi
from http.server import BaseHTTPRequestHandler, HTTPServer

from flask import Flask
import waitress
import sys


def main(image_url, port):
	app = Flask(__name__)
	api = ScoreApi(image_url, 2)

	@app.route("/", methods=['GET'])
	def index():
		return { "score:": api.fetch_scores() }

	waitress.serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
	image_url = sys.argv[1]
	port = sys.argv[2]

	main(image_url, port)

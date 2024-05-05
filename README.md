# Goal sensor

Custom component to track when a team scores a goal

# Setup

* Install python 3.10 or later:
	* `brew install python`
	* `ln -s -f /opt/homebrew/bin/python3 /usr/local/bin/python`
* Install tesseract
	* `brew install tesseract`
* Install pip dependencies:
	* `pip install numpy`
	* `pip install pytesseract`
	* `pip install python-opencv`
	* `pip install requests`
	* `pip install flask`
	* `pip install waitress`

# Example commands

* Running server:
	`python score_server.py --score_reader discovery2024 --url http://<ip-adress>:8090/json-rpc --port 8090`

* Executing tests:
	`python test_extract_score.py`

* Extracting score from image:
	`python extract_score.py test_images/discovery_2024/bkh_hif/2_1.jpg --save_images`
# Goal sensor

Custom component to track when a team scores a goal

# Setup

* Install python 3.10 or later:
	* `brew install python`
	* `ln -s -f /opt/homebrew/bin/python3 /usr/local/bin/python`
* Install tesseract
	* `brew install tesseract`
* Install pip dependencies:
	* `pip install -r requirements.txt`

On Linux:
* apt-get install git python3 python3-pip ffmpeg libsm6 libxext6

# Example commands

* Running server:
	`python score_server.py --score_reader discovery2024 --url http://<ip-adress>:8090/json-rpc --port 8642 --no_signal no_signal.jpg`

* Executing tests:
	`python test_extract_score.py`

* Extracting score from image:
	`python extract_score.py test_images/discovery_2024/bkh_hif/2_1.jpg --save_images`

# Install as a service

Example:
```
[Unit]
Description = Score Server
After = network.target

[Service]
Type = simple
WorkingDirectory = <dir>/goal_sensor/score_server/
ExecStart = python3 score_server.py --score_reader discovery2024 --no_signal_image no_signal.jpg --port 8642 --url "http://<ip-adress>:8090/json-rpc"
User = root
Group = root
Restart = on-failure
SyslogIdentifier = scoreserver
RestartSec = 5
TimeoutStartSec = infinity

[Install]
WantedBy = multi-user.target
```

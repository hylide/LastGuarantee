#!/bin/sh
python app.py &
cd files
python -m SimpleHTTPServer 5557

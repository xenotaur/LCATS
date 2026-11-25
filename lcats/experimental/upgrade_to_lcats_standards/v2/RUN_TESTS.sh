#!/bin/sh
set -eu
python -m unittest discover -s tests -t . -p "*_test.py" -v

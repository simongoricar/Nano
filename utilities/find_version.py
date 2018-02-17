# coding=utf-8
import re
import os, sys

########
# This script finds the current version
# It is intended to be piped to a file though a bash script (it writes into stdout)
########

version_pattern = re.compile(r"^__version__\s*=\s*[\"'](.*)[\"']", re.MULTILINE)

PATH = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(PATH, "..", "nano.py")) as nano:
    VERSION = re.search(version_pattern, nano.read()).groups()[0]
    print(VERSION)

#!/usr/bin/env python3
"""Exit 0 if every file in data/ matches the committed version apart from timestamps."""
import glob
import json
import subprocess
import sys


def strip_times(data):
    if isinstance(data, dict):
        return {k: strip_times(v) for k, v in data.items() if k != "generated"}
    if isinstance(data, list):
        return [strip_times(v) for v in data]
    return data


for path in sorted(glob.glob("data/*.json")):
    try:
        old = json.loads(subprocess.check_output(["git", "show", "HEAD:" + path], stderr=subprocess.DEVNULL))
    except subprocess.CalledProcessError:
        sys.exit(1)  # a new file
    with open(path, encoding="utf-8") as f:
        new = json.load(f)
    if strip_times(old) != strip_times(new):
        sys.exit(1)
sys.exit(0)

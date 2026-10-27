#!/usr/bin/env python3
"""Exit 0 if data/cameras.json matches the committed version apart from its timestamp."""
import json
import subprocess
import sys

try:
    old = json.loads(subprocess.check_output(["git", "show", "HEAD:data/cameras.json"]))
except subprocess.CalledProcessError:
    sys.exit(1)  # not committed yet
new = json.load(open("data/cameras.json", encoding="utf-8"))
old.pop("generated", None)
new.pop("generated", None)
sys.exit(0 if old == new else 1)

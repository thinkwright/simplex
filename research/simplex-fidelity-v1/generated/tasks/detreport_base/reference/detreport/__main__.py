import json
import sys

from .public import build_report

with open(sys.argv[1], encoding='utf-8') as handle:
    events = json.load(handle)
print(build_report(events))

#!/bin/bash
# Rebuild every example. Run from the examples folder.
S=../skills/content-card-designer/scripts/cardkit.py
python3 $S build ctd/spec.json --out ctd/result
python3 $S directions ctd/spec.json --moods warm,efficient,knowledge,story --out ctd/directions
python3 $S build product/spec.json --out product/result
for k in cover-wide cover-square avatar; do python3 $S build multiformat/$k.json --out multiformat/result-$k; done

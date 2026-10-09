#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
# Macros are editable. build_lab.py regenerates defaults; this runner uses them.
for scenario in control backscatter scene; do
  bash scripts/run_topas.sh "lab_${scenario}.txt" "results/$scenario"
  .venv/bin/python scripts/plot_spectrum.py --results-dir "results/$scenario"
done
mv g4_00.wrl results/scene/geometry.wrl
mv g4_01.wrl results/scene/trajectories.wrl
.venv/bin/python scripts/analyze_lab.py
echo "Comparison: $PWD/results/comparison.png"
echo "Scene: $PWD/results/scene.html"

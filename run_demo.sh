#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
bash scripts/run_topas.sh
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/plot_spectrum.py
echo "Spectrum saved to $PWD/results/spectrum.png"

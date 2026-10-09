#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image="opentopas/opentopas@sha256:e9e56294fac4e43ee77d0cc524a8411ce0637ffd8ca61992462dcfa2d774618e"
input="${1:-labr3.txt}"
output_dir="${2:-results}"
bash scripts/setup_data.sh
mkdir -p "$output_dir"
docker run --rm \
  --mount "type=bind,src=$PWD,dst=/simulations" \
  --mount "type=bind,src=$PWD/.cache/g4data,dst=/Applications/G4Data,readonly" \
  "$image" "$input" 2>&1 | tee "$output_dir/topas.log"
cp "$input" "$output_dir/input.txt"

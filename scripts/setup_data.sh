#!/usr/bin/env bash
# Minimal real datasets for Geant4 11.3.2 electromagnetic-only transport.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache/g4data .cache/downloads
while read -r archive directory checksum; do
  if [[ -f ".cache/g4data/$directory/.complete" ]]; then
    continue
  fi
  file=".cache/downloads/$archive.tar.gz"
  if [[ ! -f "$file" ]]; then
    echo "Downloading $archive from CERN..."
    curl -fL --retry 3 "https://cern.ch/geant4-data/datasets/$archive.tar.gz" -o "$file.part"
    mv "$file.part" "$file"
  fi
  actual=$(python3 -c 'import hashlib,sys; h=hashlib.md5(); f=open(sys.argv[1],"rb"); [h.update(b) for b in iter(lambda:f.read(1048576),b"")]; print(h.hexdigest())' "$file")
  [[ "$actual" == "$checksum" ]] || { echo "Checksum failed: $file" >&2; exit 1; }
  echo "Extracting $directory..."
  tar -xzf "$file" -C .cache/g4data
  touch ".cache/g4data/$directory/.complete"
done <<'DATASETS'
G4EMLOW.8.6.1 G4EMLOW8.6.1 9db67a37acc3eae9b0ffdace41a23b74
G4ENSDFSTATE.3.0 G4ENSDFSTATE3.0 c500728534ce3e9fb2fefa0112eb3a74
G4PhotonEvaporation.6.1 PhotonEvaporation6.1 92d68b937cdad0fd49892a66878863de
DATASETS

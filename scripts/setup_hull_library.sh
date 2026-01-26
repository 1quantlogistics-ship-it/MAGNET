#!/usr/bin/env bash
set -euo pipefail

# MAGNET bootstrap helper: clone ShipD hull dataset (automated).
#
# This script is intentionally simple and idempotent. It is used to populate a
# local cache of the ShipD dataset that can then be imported by
# `magnet/bootstrap/import_shipd.py`.
#
# NOTE: This is a convenience helper, not a test dependency.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${ROOT_DIR}/data/hull_library/shipd"
REPO_URL="https://github.com/noahbagz/ShipD.git"

mkdir -p "$(dirname "${DEST_DIR}")"

if [ -d "${DEST_DIR}/.git" ]; then
  echo "ShipD already present at: ${DEST_DIR}"
  echo "Pulling latest (best effort)..."
  git -C "${DEST_DIR}" pull --ff-only || true
else
  echo "Cloning ShipD into: ${DEST_DIR}"
  git clone --depth 1 "${REPO_URL}" "${DEST_DIR}"
fi

echo "Done."


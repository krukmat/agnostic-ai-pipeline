#!/usr/bin/env bash
set -euo pipefail

# Minimal wrapper to configure target and build using ESP‑IDF.
# Avoids shell chaining in YAML (blocked by validator) and keeps logic isolated.

idf.py set-target esp32c3
idf.py build


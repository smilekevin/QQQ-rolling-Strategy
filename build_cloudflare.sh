#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install -r requirements.txt
python scripts/check_build_runtime.py
python scripts/build_report.py

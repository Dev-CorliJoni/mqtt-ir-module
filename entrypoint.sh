#!/usr/bin/env bash
# entrypoint.sh
set -euo pipefail

exec uvicorn main:app --host 0.0.0.0 --port 80
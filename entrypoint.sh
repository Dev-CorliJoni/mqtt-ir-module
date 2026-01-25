#!/usr/bin/env bash
# entrypoint.sh
set -euo pipefail

start_mode="${START_MODE:-hub}"
start_mode="${start_mode,,}"

case "${start_mode}" in
    agent)
        exec uvicorn agent_main:app --host 0.0.0.0 --port 80
        ;;
    hub|"")
        exec uvicorn main:app --host 0.0.0.0 --port 80
        ;;
    *)
        echo "Unsupported START_MODE: ${start_mode}" >&2
        exit 1
        ;;
esac

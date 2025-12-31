#!/usr/bin/env bash
set -euo pipefail

mkdir -p /var/run/lirc

# start lircd in the background
lircd --nodaemon=false

exec python3 /opt/app/main.py
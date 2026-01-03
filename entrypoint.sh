#!/usr/bin/env bash
# entrypoint.sh
set -euo pipefail

: "${IR_DEVICE:=/dev/lirc0}"

LIRC_OPTIONS="/etc/lirc/lirc_options.conf"
if [[ -f "${LIRC_OPTIONS}" ]]; then
  # Escape characters that are special in sed replacement
  IR_DEVICE_ESCAPED="$(printf '%s' "${IR_DEVICE}" | sed -e 's/[&|]/\\&/g')"
  sed -i -E "s|^(\s*device\s*=\s*).*$|\1${IR_DEVICE_ESCAPED}|" "${LIRC_OPTIONS}"
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
# mqtt-ir-module

Local web UI and HTTP API to learn and transmit infrared (IR) remote codes using `ir-ctl` and `/dev/lirc*` devices.

## What it does
- Learn IR button presses from a receiver and store raw pulse timing.
- Send stored codes through an IR transmitter.
- Provide a browser UI and a REST API.

## Requirements
- Linux with IR devices at `/dev/lirc*`.
- `ir-ctl` available (the Docker image includes `v4l-utils`).

## Quick start (Docker)
Build and run with a single IR device used for both receive and send:

```bash
docker build -t mqtt-ir-module .
docker run --name mqtt-ir-module \
  --restart unless-stopped \
  --device /dev/lirc0:/dev/lirc0 \
  -v "$PWD/data:/data" \
  -e IR_RX_DEVICE=/dev/lirc0 \
  -e IR_TX_DEVICE=/dev/lirc0 \
  -p 8000:80 \
  mqtt-ir-module
```

If RX and TX are separate devices, map both and set both env vars:

```bash
docker run --name mqtt-ir-module \
  --restart unless-stopped \
  --device /dev/lirc0:/dev/lirc0 \
  --device /dev/lirc1:/dev/lirc1 \
  -v "$PWD/data:/data" \
  -e IR_RX_DEVICE=/dev/lirc1 \
  -e IR_TX_DEVICE=/dev/lirc0 \
  -p 8000:80 \
  mqtt-ir-module
```

Open the UI:
- `http://<host>:8000/`

The API is always at `/api` (and also at `<PUBLIC_BASE_URL>/api` if you use a base path).
If you set `PUBLIC_BASE_URL`, open the UI at that path (example: `http://<host>:8000/mqtt-ir-module/`).

For a docker-compose example, see:
- [`docker-setup.md`](docker-setup.md)

## Configuration
All configuration is via environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `IR_RX_DEVICE` | `/dev/lirc0` | Device used for receiving IR. |
| `IR_TX_DEVICE` | `IR_RX_DEVICE` | Device used for sending IR. |
| `IR_DEVICE` | `/dev/lirc0` | Legacy fallback for `IR_RX_DEVICE`. |
| `IR_WIDEBAND` | `false` | Adds `--wideband` to `ir-ctl` receive. |
| `DATA_DIR` | `/data` | Storage directory (SQLite DB at `ir.db`). |
| `DEBUG` | `false` | If true, stores raw capture takes. |
| `API_KEY` | empty | If set, write endpoints require `X-API-Key`. |
| `PUBLIC_API_KEY` | empty | Injects API key into the UI (exposes it to browsers). |
| `PUBLIC_BASE_URL` | `/` | Base path for hosting under a sub-path. |

If you set `API_KEY`, the UI will not be able to write unless you also set `PUBLIC_API_KEY` or inject `X-API-Key` via a reverse proxy.

## Hardware and OS setup
You need Linux IR devices at `/dev/lirc*`. For Raspberry Pi wiring and overlays, see:
- [`raspberrypi-ir-setup.md`](raspberrypi-ir-setup.md)

Quick check on the host:
```bash
ls -l /dev/lirc*
```

## Using the UI
1. Open the UI and check the Health card for RX/TX device paths.
2. Create a remote.
3. Start the learning wizard and capture a press (and optional hold).
4. Use the remote page to send press/hold.

Note: Sending is blocked while a learning session is active.

## API reference
Swagger UI is available at:
- `/api/docs`

OpenAPI schema:
- `/api/openapi.json`

Full endpoint details:
- [`backend/API.md`](backend/API.md)

## Reverse proxy (optional)
If you host under a sub-path or need to inject `X-API-Key`, see:
- [`reverse-proxy.md`](reverse-proxy.md)

## UI notes
UI overview and learning flow:
- [`website.md`](website.md)

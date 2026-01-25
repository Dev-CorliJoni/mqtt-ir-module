# Docker setup

## Environment variables

### Backend
- `API_KEY` (optional): If set, write endpoints require `X-API-Key`.
- `IR_RX_DEVICE` (default: `/dev/lirc0`)
- `IR_TX_DEVICE` (default: `IR_RX_DEVICE`)
- `IR_DEVICE` (default: `/dev/lirc0`, legacy fallback for `IR_RX_DEVICE`)
- `DATA_DIR` (default: `/data`)
- `DEBUG` (default: `false`)
- `IR_WIDEBAND` (default: `false`)

Agent ID persistence:
- Stored at `${DATA_DIR}/agent/agent_id`
- Keep the `/data` volume to retain the same ID across updates

### UI base path (reverse-proxy sub-path hosting)
- `PUBLIC_BASE_URL` (default: `/`)

`PUBLIC_BASE_URL` can be **any path**, with or without trailing slash, for example:
- `/`
- `/mqtt-ir-module`
- `/mqtt-ir-module/`
- `/a`
- `/and/more/paths`

The backend injects this into `index.html` at runtime and the frontend uses it for:
- router basename
- API base URL (`{PUBLIC_BASE_URL}/api`)

### Optional (not recommended for security)
- `PUBLIC_API_KEY` (optional):
  - If set, it will be injected into the frontend runtime config, and the frontend will send it as `X-API-Key`.
  - This exposes the key to clients that can load the UI.
  - Prefer reverse proxy header injection when `API_KEY` is used.

## Example docker-compose

```yaml
services:
  mqtt-ir-module:
    image: your-image
    container_name: mqtt-ir-module
    restart: unless-stopped

    devices:
      - "/dev/lirc0:/dev/lirc0"
      # If RX and TX are separate devices:
      # - "/dev/lirc1:/dev/lirc1"

    volumes:
      - "./data:/data"

    environment:
      - IR_RX_DEVICE=/dev/lirc0
      - IR_TX_DEVICE=/dev/lirc0
      - DATA_DIR=/data
      - DEBUG=false
      - IR_WIDEBAND=false
      - PUBLIC_BASE_URL=/mqtt-ir-module/

      # Optional:
      # - API_KEY=change-me
      # - PUBLIC_API_KEY=change-me

    ports:
      - "8000:80"
```

Open:
- UI: `http://<host>:8000/mqtt-ir-module/`
- API: `http://<host>:8000/mqtt-ir-module/api/...`
```

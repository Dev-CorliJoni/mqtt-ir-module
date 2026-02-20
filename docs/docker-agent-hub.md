# Docker Mode: `ir-agent-hub`

This mode runs Hub + integrated local IR agent in one container.

## Build

```bash
docker build --target ir-agent-hub -t mqtt-ir-agent-hub:latest .
```

## Run

```bash
docker run --rm -p 8080:80 \
  --device /dev/lirc0:/dev/lirc0 \
  --device /dev/lirc1:/dev/lirc1 \
  -e DATA_DIR=/data \
  -e SETTINGS_MASTER_KEY=change-me \
  -v ir_hub_data:/data \
  mqtt-ir-agent-hub:latest
```

## Required

- IR devices mapped into container (`IR_RX_DEVICE`, `IR_TX_DEVICE` defaults are `/dev/lirc0`, `/dev/lirc1`)
- `DATA_DIR` (recommended persistent volume)
- `SETTINGS_MASTER_KEY` when MQTT password should be stored from UI

## Optional

- `IR_RX_DEVICE`, `IR_TX_DEVICE`
- `IR_WIDEBAND`
- `API_KEY`
- `PUBLIC_BASE_URL`
- `PUBLIC_API_KEY`
- `DEBUG`

MQTT settings for Hub are configured in UI and stored in DB (same as `ir-hub`).

## Defaults in image

- `START_MODE=hub`
- `LOCAL_AGENT_ENABLED=true`

`LOCAL_AGENT_ENABLED=true` forces local integrated agent registration in Hub mode.

## Notes

- Internal local agent does not require MQTT to execute IR.
- External MQTT agents can still be paired and used in parallel.
- `hub_is_agent` is treated as read-only in UI/API and controlled by `LOCAL_AGENT_ENABLED`.

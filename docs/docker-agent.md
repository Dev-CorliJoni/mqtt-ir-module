# Docker Mode: `ir-agent`

This mode runs standalone agent runtime as a background MQTT process (no frontend and no HTTP API).

## Build

```bash
docker build --target ir-agent -t mqtt-ir-agent:latest .
```

## Run

```bash
docker run --rm \
  --device /dev/lirc0:/dev/lirc0 \
  --device /dev/lirc1:/dev/lirc1 \
  -e MQTT_HOST=broker.local \
  -e MQTT_PORT=1883 \
  -e MQTT_USERNAME=user \
  -e MQTT_PASSWORD=pass \
  -e DATA_DIR=/data \
  -v ir_agent_data:/data \
  mqtt-ir-agent:latest
```

## Required

- `MQTT_HOST` (agent needs broker access for pairing/transport)
- IR devices mapped into container (for send/learn)

## Optional

- `MQTT_PORT`
- `MQTT_USERNAME`
- `MQTT_PASSWORD`
- `AGENT_PAIRING_RESET` (clear stored pairing binding on startup)
- `IR_RX_DEVICE`, `IR_TX_DEVICE`
- `IR_WIDEBAND`
- `DEBUG`

## Defaults in image

- `START_MODE=agent`

## Runtime behavior

- Agent MQTT identity is derived from jmqtt client identity (stable deterministic client id generation).
- Pairing listens on `ir/pairing/open` for 5 minutes after startup when agent is unbound.
- Accepted hub binding is persisted in app settings storage.

## Notes

- This image does not host the Hub UI.
- This image does not expose an HTTP API.
- Hub pairing is initiated from Hub side (Agents page).

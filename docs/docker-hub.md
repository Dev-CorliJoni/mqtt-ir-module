# Docker Mode: `ir-hub`

This mode runs the Hub backend + frontend without local IR hardware dependencies.

## Build

```bash
docker build --target ir-hub -t mqtt-ir-hub:latest .
```

## Run

```bash
docker run --rm -p 8080:80 \
  -e DATA_DIR=/data \
  -e SETTINGS_MASTER_KEY=change-me \
  -v ir_hub_data:/data \
  mqtt-ir-hub:latest
```

## Required

- `DATA_DIR` (recommended persistent volume)
- `SETTINGS_MASTER_KEY` when MQTT password should be stored from UI

## Optional

- `API_KEY` (protect write endpoints)
- `PUBLIC_BASE_URL` (reverse proxy sub-path)
- `PUBLIC_API_KEY` (not recommended for public exposure)
- `DEBUG`

MQTT settings for Hub are configured in UI and stored in DB:

- `mqtt_host`
- `mqtt_port`
- `mqtt_username`
- `mqtt_password` (encrypted)
- `mqtt_instance`
- `homeassistant_enabled`

## Defaults in image

- `START_MODE=hub`
- `LOCAL_AGENT_ENABLED=false`

`LOCAL_AGENT_ENABLED=false` means no integrated local IR agent is registered.

## Notes

- This image can run with or without MQTT configured.
- Pairing for external agents is manual from the Agents page.
- Home Assistant integration is available only in hub role and only when enabled in settings.

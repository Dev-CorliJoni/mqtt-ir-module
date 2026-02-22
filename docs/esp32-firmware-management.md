# ESP32 Firmware Catalog and OTA Guide

This project serves ESP32 firmware files from the Hub and triggers OTA over MQTT.

## 1. Build firmware

From repository root:

```bash
cd esp-agent
pio run -e esp32dev
```

PlatformIO output binaries are typically in:

`esp-agent/.pio/build/esp32dev/`

## 2. Copy firmware file to Hub firmware directory

Default firmware directory inside Hub runtime:

`/data/firmware/files/`

Default catalog file:

`/data/firmware/catalog.json`

The Docker image initializes firmware layout from `/opt/app/firmware_template` on every container start.
`catalog.json` in the runtime firmware directory is overwritten by the template file at startup.

Copy your OTA `.bin` file into `/data/firmware/files/`.

Example filename:

`esp32-ir-client-v0.1.0.bin`

## 3. Compute SHA-256 checksum

Use one of these commands:

```bash
sha256sum /data/firmware/files/esp32-ir-client-v0.1.0.bin
```

```bash
shasum -a 256 /data/firmware/files/esp32-ir-client-v0.1.0.bin
```

Copy the 64-char lowercase hash.

## 4. Update catalog.json

Edit `/data/firmware/catalog.json`.

The file is auto-created with a placeholder entry (`0.0.1`, `installable=false`).

Set `installable=true` only when:

- `ota_file` exists in `/data/firmware/files/`
- `ota_sha256` is correct

Example installable entry:

```json
{
  "agent_type": "esp32",
  "version": "0.1.0",
  "installable": true,
  "ota_file": "esp32-ir-client-v0.1.0.bin",
  "ota_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "factory_file": "esp32-ir-client-v0.1.0.factory.bin",
  "factory_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
  "notes": "stable"
}
```

## 5. Verify from API

Check catalog visibility:

```bash
curl http://<hub-host>/api/firmware?agent_type=esp32
```

Check Web Tools manifest:

```bash
curl http://<hub-host>/api/firmware/webtools-manifest?agent_type=esp32
```

## 6. Trigger OTA from UI

1. Open `Agents` page.
2. Select an ESP32 agent with `Update available`.
3. Choose version (latest is preselected).
4. Confirm update.
5. Agent downloads firmware, verifies SHA-256, installs, and reboots.

## 7. Notes

- Version format is strict `x.y.z`.
- Downgrades are allowed from UI.
- OTA command includes checksum and agent verifies it before finalizing update.

# mqtt-ir-module API

FastAPI exposes interactive Swagger UI at:
- `GET /docs`
- OpenAPI schema: `GET /openapi.json`

## Authentication

If `API_KEY` environment variable is set, write requests must include header:

`X-API-Key: <API_KEY>`

Read-only endpoints do not require the header.

## Data Model (DB)

- **Remote**: a physical remote control.
- **Button**: a named button for a remote.
- **Button signals**: raw pulse/space timing captured from `/dev/lirc0` using `ir-ctl`.

Signals are stored as space-separated signed microseconds:

Example: `890 -906 871 -906 1781 -885 ...`

## Endpoints

### Health

`GET /health`

### Remotes CRUD

#### Create remote

`POST /remotes`

Body:
```json
{ "name": "TV Remote" }
```

#### List remotes

`GET /remotes`

#### Update remote (rename + optional transmit defaults)

`PUT /remotes/{remote_id}`

Body:
```json
{
  "name": "TV Remote",
  "carrier_hz": 38000,
  "duty_cycle": 33,
  "gap_us_default": 125000
}
```

#### Delete remote

`DELETE /remotes/{remote_id}`

### Buttons CRUD

#### List buttons for remote

`GET /remotes/{remote_id}/buttons`

Returns `has_press` / `has_hold` flags.

#### Rename button

`PUT /buttons/{button_id}`

Body:
```json
{ "name": "VOLUME_UP" }
```

#### Delete button

`DELETE /buttons/{button_id}`

### Learning (automated tool handling)

#### Start learning session

`POST /learn/start`

Body:
```json
{ "remote_id": 1, "extend": false }
```

- `extend=false`: deletes all existing buttons/signals for the remote (remote stays)
- `extend=true`: keeps existing buttons and continues with the next `BTN_XXXX` name

#### Capture press or hold

`POST /learn/capture`

Body (press):
```json
{
  "remote_id": 1,
  "mode": "press",
  "takes": 5,
  "timeout_ms": 3000,
  "overwrite": false,
  "button_name": null
}
```

- If `button_name` is omitted/null for `press`, the service creates `BTN_0001`, `BTN_0002`, ...
- `takes` controls how many separate presses you will perform.

Body (hold):
```json
{
  "remote_id": 1,
  "mode": "hold",
  "timeout_ms": 4000,
  "overwrite": false,
  "button_name": "VOLUME_UP"
}
```

- `hold` requires that the button already has a `press` captured.
- For `hold`, if `button_name` is omitted/null, the service uses the last captured button in the current session.

Errors:
- `408`: no signal within `timeout_ms`
- `409`: session/overwrite conflict

#### Stop learning

`POST /learn/stop`

#### Learning status + log

`GET /learn/status`

Includes `logs` (useful for UI/debug).

### Sending

`POST /send`

Body (press):
```json
{ "button_id": 10, "mode": "press" }
```

Body (hold):
```json
{ "button_id": 10, "mode": "hold", "hold_ms": 800 }
```

Notes:
- Sending is disabled while a learning session is active.
- `hold` uses the captured `hold_initial` + repeated `hold_repeat` frames.

## Debug capture storage

- If `DEBUG=true`, every raw take is stored in the `captures` table.
- If `DEBUG=false`, the service clears the `captures` table on container start.

## Future extension: protocol decoding

The DB schema contains optional fields (`protocol`, `address`, `command_hex`, `decode_confidence`) reserved for a future decoder. These are currently not populated.

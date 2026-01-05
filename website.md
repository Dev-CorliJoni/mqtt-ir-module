# Website / UI guide

## Pages

- Home: health overview + last opened remote (fallback: last updated remote)
- Remotes: create/edit/delete remotes
- Remote detail: buttons grid, send press/hold, learning wizard
- Settings: theme + language persisted in DB, runtime info

## Learning wizard

Start:
- Add buttons (extend)
- Re-learn remote (clears existing buttons) with warning modal

Flow:
1) Button setup (name + advanced capture params)
2) Capture press
3) Optional capture hold
4) Add another button or finish summary
5) Stop learning

## Common errors

- 408 (Timeout): No signal within timeout -> Retry suggested
- 409 (Conflict): Session conflict / overwrite conflict -> Retry or stop current session
- 400 (Bad request): Invalid state (e.g. hold without press) -> follow the UI hint
- 401 (Unauthorized): Write endpoints require API key -> configure proxy header injection
- 404 (Not found): Remote/Button not found

## Notes

- Sending is blocked while learning is active.
- Icons for remotes/buttons are stored in the DB.

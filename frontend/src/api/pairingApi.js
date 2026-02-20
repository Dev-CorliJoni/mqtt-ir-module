import { requestJson } from './httpClient.js'

export function getPairingStatus() {
  return requestJson('/status/pairing')
}

export function openPairing(durationSeconds = 300) {
  return requestJson('/pairing/open', {
    method: 'POST',
    body: { duration_seconds: durationSeconds },
  })
}

export function closePairing() {
  return requestJson('/pairing/close', {
    method: 'POST',
    body: {},
  })
}

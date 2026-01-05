import {requestJson} from './httpClient.js'

export function listButtons(remoteId) {
  return requestJson(`/remotes/${remoteId}/buttons`)
}

export function updateButton(buttonId, {name, icon}) {
  return requestJson(`/buttons/${buttonId}`, {
    method: 'PUT',
    body: {name, icon: icon ?? null},
  })
}

export function deleteButton(buttonId) {
  return requestJson(`/buttons/${buttonId}`, {method: 'DELETE'})
}

export function sendPress(buttonId) {
  return requestJson(
      '/send', {method: 'POST', body: {button_id: buttonId, mode: 'press'}})
}

export function sendHold(buttonId, holdMs) {
  return requestJson('/send', {
    method: 'POST',
    body: {button_id: buttonId, mode: 'hold', hold_ms: holdMs}
  })
}
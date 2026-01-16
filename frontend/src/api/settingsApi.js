import {requestJson} from './httpClient.js'

export function getSettings() {
  return requestJson('/settings')
}

export function updateSettings(settings) {
  return requestJson('/settings', {method: 'PUT', body: settings})
}

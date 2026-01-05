import {requestJson} from './httpClient.js'

export function getSettings() {
  return requestJson('/settings')
}

export function updateSettings({theme, language}) {
  return requestJson('/settings', {method: 'PUT', body: {theme, language}})
}
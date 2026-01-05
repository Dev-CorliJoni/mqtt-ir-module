import {requestJson} from './httpClient.js'

export function getHealth() {
  return requestJson('/health')
}
import {requestJson} from './httpClient.js'

export function listAgents() {
  return requestJson('/agents')
}

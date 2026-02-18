import {requestJson} from './httpClient.js'

export function listAgents() {
  return requestJson('/agents')
}

export function getAgent(agentId) {
  return requestJson(`/agents/${agentId}`)
}

export function updateAgent(agentId, payload) {
  return requestJson(`/agents/${agentId}`, {
    method: 'PUT',
    body: payload,
  })
}

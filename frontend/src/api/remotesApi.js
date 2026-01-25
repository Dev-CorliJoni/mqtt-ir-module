import {requestJson} from './httpClient.js'

export function listRemotes() {
  return requestJson('/remotes')
}

export function createRemote({name, icon}) {
  return requestJson(
      '/remotes', {method: 'POST', body: {name, icon: icon ?? null}})
}

export function updateRemote(remoteId, remote) {
  return requestJson(`/remotes/${remoteId}`, {
    method: 'PUT',
    body: {
      name: remote.name,
      icon: remote.icon ?? null,
      assigned_agent_id: remote.assigned_agent_id ?? null,
      carrier_hz: remote.carrier_hz ?? null,
      duty_cycle: remote.duty_cycle ?? null,
    },
  })
}

export function deleteRemote(remoteId) {
  return requestJson(`/remotes/${remoteId}`, {method: 'DELETE'})
}

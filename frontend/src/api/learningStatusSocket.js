import { getAppConfig } from '../utils/appConfig.js'

function buildWebSocketUrl(path) {
  const { apiBaseUrl } = getAppConfig()
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const base = apiBaseUrl.replace(/\/$/, '')

  // Support both absolute and same-origin API base URLs.
  if (base.startsWith('http://') || base.startsWith('https://')) {
    const url = new URL(`${base}${cleanPath}`)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return url.toString()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${base}${cleanPath}`
}

export function createLearningStatusSocket({
  onOpen,
  onClose,
  onError,
  onMessage,
} = {}) {
  // Use a single socket to stream status updates instead of HTTP polling.
  const socket = new WebSocket(buildWebSocketUrl('/learn/status/ws'))

  socket.onopen = () => onOpen?.()
  socket.onclose = () => onClose?.()
  socket.onerror = (event) => onError?.(event)
  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data)
      if (payload && typeof payload === 'object') onMessage?.(payload)
    } catch {
      // Ignore malformed payloads to keep the socket alive.
    }
  }

  return socket
}

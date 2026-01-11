import {getAppConfig} from '../utils/appConfig.js'

export class ApiError extends Error {
  constructor(status, message, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

function buildUrl(path) {
  const {apiBaseUrl} = getAppConfig()
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${apiBaseUrl}${cleanPath}`
}

export async function requestJson(path, {method = 'GET', body, headers} = {}) {
  const config = getAppConfig()
  const url = buildUrl(path)

  const reqHeaders = {
    ...(headers || {}),
  }

  if (body !== undefined) {
    reqHeaders['Content-Type'] = 'application/json'
  }

  // If a reverse proxy injects X-API-Key, you do not need PUBLIC_API_KEY.
  if (config.publicApiKey) {
    reqHeaders['X-API-Key'] = config.publicApiKey
  }

  let response
  try {
    response = await fetch(url, {
      method,
      headers: reqHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (e) {
    throw new ApiError(0, 'Network error', String(e))
  }

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')

  if (!response.ok) {
    let detail = response.statusText
    // Preserve structured error payloads for higher-level error mapping.
    let errorDetails = null
    if (isJson) {
      try {
        const data = await response.json()
        errorDetails = data
        if (typeof data?.detail === 'string') {
          detail = data.detail
        } else if (typeof data?.message === 'string') {
          detail = data.message
        } else if (data?.detail) {
          detail = JSON.stringify(data.detail)
        } else {
          detail = JSON.stringify(data)
        }
      } catch {
        // ignore
      }
    }
    else {
      try {
        detail = await response.text()
      } catch {
        // ignore
      }
    }
    throw new ApiError(response.status, detail || 'Request failed', errorDetails || detail)
  }

  if (response.status === 204) return null
    if (!isJson) return await response.text();
  return await response.json()
}

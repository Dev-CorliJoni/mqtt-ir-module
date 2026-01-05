function normalizeBaseUrl(raw) {
  let value = (raw || '/').trim()
  if (!value) value = '/'
  if (!value.startsWith('/')) value = `/${value}`
  if (!value.endsWith('/')) value = `${value}/`
  if (value === '//') value = '/'
  return value
}

export function getAppConfig() {
  const runtime =
      typeof window !== 'undefined' ? window.__APP_CONFIG__ : undefined
  const publicBaseUrl = normalizeBaseUrl(runtime?.publicBaseUrl || '/')
  const routerBasePath =
      publicBaseUrl === '/' ? '/' : publicBaseUrl.replace(/\/$/, '')
  const apiBaseUrl = `${publicBaseUrl.replace(/\/$/, '')}/api`

  return {
    publicBaseUrl, routerBasePath, apiBaseUrl,
        publicApiKey: (runtime?.publicApiKey || '').trim(),
        writeRequiresApiKey: Boolean(runtime?.writeRequiresApiKey),
  }
}
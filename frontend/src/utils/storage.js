export function readLocalStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

export function writeLocalStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Ignore storage errors (private mode, quota, etc.)
  }
}

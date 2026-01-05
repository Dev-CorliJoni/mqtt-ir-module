export function applyTheme(theme) {
  const value = theme || 'system'
  document.documentElement.setAttribute('data-theme', value)
}
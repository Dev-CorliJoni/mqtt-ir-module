import {mdiArrowLeft, mdiCheckCircleOutline, mdiChevronDown, mdiChevronLeft, mdiChevronRight, mdiChevronUp, mdiCogOutline, mdiFastForward, mdiGestureTapButton, mdiHomeOutline, mdiInformationOutline, mdiMenu, mdiNumeric, mdiPause, mdiPlay, mdiPower, mdiPowerStandby, mdiRemote, mdiRemoteTv, mdiRewind, mdiSkipNext, mdiSkipPrevious, mdiStop, mdiTelevision, mdiVideoInputHdmi, mdiVolumeMinus, mdiVolumeMute, mdiVolumePlus,} from '@mdi/js'

export const DEFAULT_REMOTE_ICON = 'remoteTv'
export const DEFAULT_BUTTON_ICON = 'tapButton'

export const ICONS = [
  // Remote
  { key: 'remoteTv', category: 'remote', path: mdiRemoteTv },
  { key: 'remote', category: 'remote', path: mdiRemote },
  { key: 'tv', category: 'remote', path: mdiTelevision },

  // Power / volume
  { key: 'power', category: 'power', path: mdiPower },
  { key: 'standby', category: 'power', path: mdiPowerStandby },
  { key: 'volumeUp', category: 'volume', path: mdiVolumePlus },
  { key: 'volumeDown', category: 'volume', path: mdiVolumeMinus },
  { key: 'mute', category: 'volume', path: mdiVolumeMute },

  // Navigation
  { key: 'up', category: 'navigation', path: mdiChevronUp },
  { key: 'down', category: 'navigation', path: mdiChevronDown },
  { key: 'left', category: 'navigation', path: mdiChevronLeft },
  { key: 'right', category: 'navigation', path: mdiChevronRight },
  { key: 'ok', category: 'navigation', path: mdiCheckCircleOutline },
  { key: 'home', category: 'navigation', path: mdiHomeOutline },
  { key: 'back', category: 'navigation', path: mdiArrowLeft },
  { key: 'menu', category: 'navigation', path: mdiMenu },

  // Media
  { key: 'play', category: 'media', path: mdiPlay },
  { key: 'pause', category: 'media', path: mdiPause },
  { key: 'stop', category: 'media', path: mdiStop },
  { key: 'rewind', category: 'media', path: mdiRewind },
  { key: 'fastForward', category: 'media', path: mdiFastForward },
  { key: 'next', category: 'media', path: mdiSkipNext },
  { key: 'previous', category: 'media', path: mdiSkipPrevious },

  // Input / misc
  { key: 'inputHdmi', category: 'input', path: mdiVideoInputHdmi },
  { key: 'info', category: 'input', path: mdiInformationOutline },
  { key: 'settings', category: 'input', path: mdiCogOutline },
  { key: 'channel', category: 'input', path: mdiNumeric },

  // Default button icon
  { key: 'tapButton', category: 'default', path: mdiGestureTapButton },
]

export const ICON_CATEGORIES = Array.from(new Set(ICONS.map((i) => i.category)))

export function findIconPath(iconKey) {
  const found = ICONS.find((i) => i.key === iconKey)
  if (found) return found.path
  const fallback = ICONS.find((i) => i.key === DEFAULT_BUTTON_ICON)
  return fallback ? fallback.path : mdiGestureTapButton
}

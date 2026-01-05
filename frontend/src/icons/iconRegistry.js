import {mdiArrowLeft, mdiCheckCircleOutline, mdiChevronDown, mdiChevronLeft, mdiChevronRight, mdiChevronUp, mdiCogOutline, mdiFastForward, mdiGestureTapButton, mdiHomeOutline, mdiInformationOutline, mdiMenu, mdiNumeric, mdiPause, mdiPlay, mdiPower, mdiPowerStandby, mdiRemote, mdiRemoteTv, mdiRewind, mdiSkipNext, mdiSkipPrevious, mdiStop, mdiTelevision, mdiVideoInputHdmi, mdiVolumeMinus, mdiVolumeMute, mdiVolumePlus,} from '@mdi/js'

export const DEFAULT_REMOTE_ICON = 'remoteTv'
export const DEFAULT_BUTTON_ICON = 'tapButton'

export const ICONS =
    [
      // Remote
      {
        key: 'remoteTv',
        label: 'Remote TV',
        category: 'Remote',
        path: mdiRemoteTv
      },
      {key: 'remote', label: 'Remote', category: 'Remote', path: mdiRemote},
      {key: 'tv', label: 'TV', category: 'Remote', path: mdiTelevision},

      // Power / volume
      {key: 'power', label: 'Power', category: 'Power', path: mdiPower},
      {
        key: 'standby',
        label: 'Standby',
        category: 'Power',
        path: mdiPowerStandby
      },
      {
        key: 'volumeUp',
        label: 'Volume +',
        category: 'Volume',
        path: mdiVolumePlus
      },
      {
        key: 'volumeDown',
        label: 'Volume -',
        category: 'Volume',
        path: mdiVolumeMinus
      },
      {key: 'mute', label: 'Mute', category: 'Volume', path: mdiVolumeMute},

      // Navigation
      {key: 'up', label: 'Up', category: 'Navigation', path: mdiChevronUp},
      {
        key: 'down',
        label: 'Down',
        category: 'Navigation',
        path: mdiChevronDown
      },
      {
        key: 'left',
        label: 'Left',
        category: 'Navigation',
        path: mdiChevronLeft
      },
      {
        key: 'right',
        label: 'Right',
        category: 'Navigation',
        path: mdiChevronRight
      },
      {
        key: 'ok',
        label: 'OK',
        category: 'Navigation',
        path: mdiCheckCircleOutline
      },
      {
        key: 'home',
        label: 'Home',
        category: 'Navigation',
        path: mdiHomeOutline
      },
      {key: 'back', label: 'Back', category: 'Navigation', path: mdiArrowLeft},
      {key: 'menu', label: 'Menu', category: 'Navigation', path: mdiMenu},

      // Media
      {key: 'play', label: 'Play', category: 'Media', path: mdiPlay},
      {key: 'pause', label: 'Pause', category: 'Media', path: mdiPause},
      {key: 'stop', label: 'Stop', category: 'Media', path: mdiStop},
      {key: 'rewind', label: 'Rewind', category: 'Media', path: mdiRewind},
      {
        key: 'fastForward',
        label: 'Fast forward',
        category: 'Media',
        path: mdiFastForward
      },
      {key: 'next', label: 'Next', category: 'Media', path: mdiSkipNext},
      {
        key: 'previous',
        label: 'Previous',
        category: 'Media',
        path: mdiSkipPrevious
      },

      // Input / misc
      {
        key: 'inputHdmi',
        label: 'HDMI',
        category: 'Input',
        path: mdiVideoInputHdmi
      },
      {
        key: 'info',
        label: 'Info',
        category: 'Input',
        path: mdiInformationOutline
      },
      {
        key: 'settings',
        label: 'Settings',
        category: 'Input',
        path: mdiCogOutline
      },
      {key: 'channel', label: 'Channel', category: 'Input', path: mdiNumeric},

      // Default button icon
      {
        key: 'tapButton',
        label: 'Button',
        category: 'Default',
        path: mdiGestureTapButton
      },
    ]

    export const ICON_CATEGORIES =
        Array.from(new Set(ICONS.map((i) => i.category)))

export function findIconPath(iconKey) {
  const found = ICONS.find((i) => i.key === iconKey)
  if (found) return found.path
  const fallback = ICONS.find((i) => i.key === DEFAULT_BUTTON_ICON)
  return fallback ? fallback.path : mdiGestureTapButton
}
import { ApiError } from '../api/httpClient.js'

const CODE_MAP = {
  invalid_api_key: {
    kind: 'unauthorized',
    titleKey: 'errors.unauthorizedTitle',
    bodyKey: 'errors.unauthorizedBody',
  },
  learning_active: {
    kind: 'conflict',
    titleKey: 'errors.conflictTitle',
    bodyKey: 'errors.learningActiveBody',
  },
  signal_exists: {
    kind: 'conflict',
    titleKey: 'errors.conflictTitle',
    bodyKey: 'errors.signalExistsBody',
  },
  send_while_learning: {
    kind: 'conflict',
    titleKey: 'errors.conflictTitle',
    bodyKey: 'errors.sendWhileLearningBody',
  },
  name_required: {
    kind: 'badRequest',
    titleKey: 'errors.badRequestTitle',
    bodyKey: 'errors.nameRequiredBody',
  },
  settings_missing: {
    kind: 'badRequest',
    titleKey: 'errors.badRequestTitle',
    bodyKey: 'errors.settingsMissingBody',
  },
  signal_missing: {
    kind: 'badRequest',
    titleKey: 'errors.badRequestTitle',
    bodyKey: 'errors.signalMissingBody',
  },
}

// Match backend detail strings to friendly categories when no structured code is provided.
const CONFLICT_PATTERNS = [
  {
    bodyKey: 'errors.sendWhileLearningBody',
    patterns: ['cannot send while learning is active'],
  },
  {
    bodyKey: 'errors.learningActiveBody',
    patterns: [
      'learning session is already running',
      'learning session is running for a different remote',
    ],
  },
  {
    bodyKey: 'errors.signalExistsBody',
    patterns: ['signal already exists'],
  },
]

const BAD_REQUEST_PATTERNS = [
  {
    bodyKey: 'errors.nameRequiredBody',
    patterns: ['name must not be empty', 'button_name is required'],
  },
  {
    bodyKey: 'errors.settingsMissingBody',
    patterns: ['at least one setting must be provided'],
  },
  {
    bodyKey: 'errors.signalMissingBody',
    patterns: [
      'press must be captured before hold',
      'hold signals are missing',
      'hold gap is missing',
      'no signals for button',
      'hold capture needs at least 2 frames',
      'failed to extract a repeat frame',
      'failed to infer hold gap',
      'no tokens parsed from raw capture',
      'normalized signal is empty',
      'signal starts with a space',
      'normalized signal does not start with a pulse',
      'normalized signal does not end with a pulse',
    ],
  },
]

const NOT_FOUND_PATTERNS = ['unknown remote_id', 'unknown button_id', 'unknown button name']

function isApiError(error) {
  return error instanceof ApiError || typeof error?.status === 'number'
}

function extractDetailText(error) {
  if (!error) return ''
  if (typeof error === 'string') return error

  const details = error.details
  if (details && typeof details === 'object') {
    if (typeof details.detail === 'string') return details.detail
    if (typeof details.message === 'string') return details.message
    if (typeof details.error === 'string') return details.error
    if (Array.isArray(details.detail)) {
      const messages = details.detail.map((item) => item?.msg).filter(Boolean)
      if (messages.length) return messages.join(' ')
    }
  }

  if (typeof error.message === 'string') return error.message
  return ''
}

function extractErrorCode(error) {
  const details = error?.details
  if (!details || typeof details !== 'object') return null

  if (typeof details.code === 'string') return details.code
  if (typeof details.error_code === 'string') return details.error_code
  if (typeof details.error?.code === 'string') return details.error.code
  if (typeof details.detail?.code === 'string') return details.detail.code
  return null
}

function matchPattern(detail, patterns) {
  if (!detail) return null
  const normalized = detail.toLowerCase()
  return patterns.find((entry) => entry.patterns.some((pattern) => normalized.includes(pattern))) || null
}

function matchList(detail, list) {
  if (!detail) return false
  const normalized = detail.toLowerCase()
  return list.some((pattern) => normalized.includes(pattern))
}

export class ApiErrorMapper {
  constructor(t) {
    this.t = t
  }

  getErrorInfo(error) {
    const detailText = extractDetailText(error)
    const isApi = isApiError(error)
    const status = isApi ? error.status ?? 0 : null
    const code = extractErrorCode(error)
    const normalizedCode = code ? String(code).toLowerCase() : null

    // Prefer structured error codes when the backend provides them.
    if (normalizedCode && CODE_MAP[normalizedCode]) {
      return CODE_MAP[normalizedCode]
    }

    if (!isApi && detailText) {
      return {
        kind: 'generic',
        titleKey: 'errors.genericTitle',
        bodyText: detailText,
      }
    }

    if (status === 0) {
      return { kind: 'offline', titleKey: 'errors.offlineTitle', bodyKey: 'errors.offlineBody' }
    }

    if (status === 401 || matchList(detailText, ['invalid api key'])) {
      return { kind: 'unauthorized', titleKey: 'errors.unauthorizedTitle', bodyKey: 'errors.unauthorizedBody' }
    }

    if (status === 408) {
      return { kind: 'timeout', titleKey: 'errors.timeoutTitle', bodyKey: 'errors.timeoutBody' }
    }

    if (status === 404 || matchList(detailText, NOT_FOUND_PATTERNS)) {
      return { kind: 'notFound', titleKey: 'errors.notFoundTitle', bodyKey: 'errors.notFoundBody' }
    }

    if (status === 409) {
      const match = matchPattern(detailText, CONFLICT_PATTERNS)
      return {
        kind: 'conflict',
        titleKey: 'errors.conflictTitle',
        bodyKey: match?.bodyKey || 'errors.conflictBody',
      }
    }

    if (status === 400 || status === 422) {
      const match = matchPattern(detailText, BAD_REQUEST_PATTERNS)
      return {
        kind: 'badRequest',
        titleKey: 'errors.badRequestTitle',
        bodyKey: match?.bodyKey || 'errors.badRequestBody',
      }
    }

    return { kind: 'generic', titleKey: 'errors.genericTitle', bodyKey: 'errors.genericBody' }
  }

  getMessage(error, fallbackKey = 'errors.genericBody') {
    const info = this.getErrorInfo(error)
    if (info.bodyText) return info.bodyText
    if (info.kind === 'generic' && fallbackKey) {
      return this.t(fallbackKey, info.bodyValues)
    }
    return this.t(info.bodyKey || fallbackKey, info.bodyValues)
  }

  getTitle(error, fallbackKey = 'errors.genericTitle') {
    const info = this.getErrorInfo(error)
    return this.t(info.titleKey || fallbackKey, info.titleValues)
  }

  getCallout(error) {
    const info = this.getErrorInfo(error)
    return {
      kind: info.kind || 'generic',
      title: this.getTitle(error),
      body: this.getMessage(error),
    }
  }
}

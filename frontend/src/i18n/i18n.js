import i18n from 'i18next'
import {initReactI18next} from 'react-i18next'

import de from './locales/de.json'
import en from './locales/en.json'
import es from './locales/es.json'
import fr from './locales/fr.json'
import hi from './locales/hi.json'
import ptPT from './locales/pt-PT.json'
import zhCN from './locales/zh-CN.json'

i18n.use(initReactI18next).init({
  resources: {
    en: {translation: en},
    de: {translation: de},
    es: {translation: es},
    'pt-PT': {translation: ptPT},
    fr: {translation: fr},
    'zh-CN': {translation: zhCN},
    hi: {translation: hi},
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {escapeValue: false},
})

export default i18n
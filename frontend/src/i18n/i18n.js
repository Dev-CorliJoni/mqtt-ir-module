import i18n from 'i18next'
import {initReactI18next} from 'react-i18next'

import ar from './locales/ar.json'
import bn from './locales/bn.json'
import de from './locales/de.json'
import en from './locales/en.json'
import es from './locales/es.json'
import fr from './locales/fr.json'
import hi from './locales/hi.json'
import id from './locales/id.json'
import ja from './locales/ja.json'
import ptPT from './locales/pt-PT.json'
import ru from './locales/ru.json'
import ur from './locales/ur.json'
import zhCN from './locales/zh-CN.json'

i18n.use(initReactI18next).init({
  resources: {
    ar: {translation: ar},
    bn: {translation: bn},
    en: {translation: en},
    de: {translation: de},
    es: {translation: es},
    'pt-PT': {translation: ptPT},
    fr: {translation: fr},
    'zh-CN': {translation: zhCN},
    hi: {translation: hi},
    id: {translation: id},
    ja: {translation: ja},
    ru: {translation: ru},
    ur: {translation: ur},
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {escapeValue: false},
})

export default i18n

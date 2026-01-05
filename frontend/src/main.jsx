import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n/i18n.js'
import { Providers } from './app/Providers.jsx'
import { createAppRouter } from './app/Router.jsx'
import { getAppConfig } from './utils/appConfig.js'

const config = getAppConfig()
const router = createAppRouter({ basename: config.routerBasePath })

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Providers router={router} />
  </React.StrictMode>,
)

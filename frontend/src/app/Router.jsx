import React from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './AppShell.jsx'
import { HomePage } from '../pages/HomePage.jsx'
import { RemotesPage } from '../pages/RemotesPage.jsx'
import { RemoteDetailPage } from '../pages/RemoteDetailPage.jsx'
import { SettingsPage } from '../pages/SettingsPage.jsx'
import { NotFoundPage } from '../pages/NotFoundPage.jsx'

export function createAppRouter({ basename }) {
  return createBrowserRouter(
    [
      {
        path: '/',
        element: <AppShell />,
        children: [
          { index: true, element: <HomePage /> },
          { path: 'remotes', element: <RemotesPage /> },
          { path: 'remotes/:remoteId', element: <RemoteDetailPage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
    { basename },
  )
}
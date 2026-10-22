import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { IntlProvider } from 'react-intl'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import { defaultLocale, messagesByLocale } from './i18n/messages'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <IntlProvider
      locale={defaultLocale}
      messages={messagesByLocale[defaultLocale]}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </IntlProvider>
  </StrictMode>,
)

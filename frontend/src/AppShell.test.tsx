import { render, screen } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { defaultLocale, en, messagesByLocale } from './i18n/messages'

function renderShell(initialRoute = '/') {
  return render(
    <IntlProvider
      locale={defaultLocale}
      messages={messagesByLocale[defaultLocale]}
    >
      <MemoryRouter initialEntries={[initialRoute]}>
        <App />
      </MemoryRouter>
    </IntlProvider>,
  )
}

describe('AppShell navigation', () => {
  it('shows primary nav labels from the English catalog', () => {
    renderShell()

    expect(
      screen.getByRole('link', { name: en['nav.exploreRoutes'] }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: en['nav.routeDetail'] }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: en['nav.tripPlanner'] }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: en['nav.myTrips'] }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: en['nav.routeWiki'] }),
    ).toBeInTheDocument()
    expect(screen.getByText(en['app.name'])).toBeInTheDocument()
  })
})

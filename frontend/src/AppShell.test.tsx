import { render, screen } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import App from './App'
import { AppShell } from './components/AppShell'
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

  it('highlights the nav item for the current section', () => {
    const { unmount } = renderShell('/')
    expect(screen.getByRole('link', { name: en['nav.exploreRoutes'] })).toHaveClass(
      'nav-link-active',
    )
    expect(
      screen.getByRole('link', { name: en['nav.routeDetail'] }),
    ).not.toHaveClass('nav-link-active')
    unmount()

    render(
      <IntlProvider locale={defaultLocale} messages={messagesByLocale[defaultLocale]}>
        <MemoryRouter
          initialEntries={['/routes/11111111-1111-4111-8111-111111111111']}
        >
          <Routes>
            <Route element={<AppShell />}>
              <Route
                path="routes/:routeId"
                element={<div>Route detail</div>}
                handle={{ navSection: 'routeDetail' }}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      </IntlProvider>,
    )
    expect(screen.getByRole('link', { name: en['nav.routeDetail'] })).toHaveClass(
      'nav-link-active',
    )
    expect(
      screen.getByRole('link', { name: en['nav.exploreRoutes'] }),
    ).not.toHaveClass('nav-link-active')
  })
})

import { FormattedMessage, useIntl } from 'react-intl'
import { NavLink, Outlet } from 'react-router-dom'
import { DEMO_PUBLISHED_ROUTE_ID } from '../data/seedRouteIds'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'nav-link nav-link-active' : 'nav-link'

export function AppShell() {
  const intl = useIntl()

  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="app-brand">
          <FormattedMessage id="app.name" />
        </p>
        <nav
          className="app-nav"
          aria-label={intl.formatMessage({ id: 'nav.ariaPrimary' })}
        >
          <NavLink to="/" end className={navLinkClass}>
            <FormattedMessage id="nav.exploreRoutes" />
          </NavLink>
          <NavLink to={`/routes/${DEMO_PUBLISHED_ROUTE_ID}`} className={navLinkClass}>
            <FormattedMessage id="nav.routeDetail" />
          </NavLink>
          <NavLink to="/plan" className={navLinkClass}>
            <FormattedMessage id="nav.tripPlanner" />
          </NavLink>
          <NavLink to="/trips" className={navLinkClass}>
            <FormattedMessage id="nav.myTrips" />
          </NavLink>
          <NavLink to="/review" className={navLinkClass}>
            <FormattedMessage id="nav.routeWiki" />
          </NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}

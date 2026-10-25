import type { ReactNode } from 'react'
import { FormattedMessage, useIntl } from 'react-intl'
import { Link, Outlet } from 'react-router-dom'
import { DEMO_PUBLISHED_ROUTE_ID } from '../data/seedRouteIds'
import type { AppNavSection } from './appNav'
import { navLinkClassName } from './appNav'
import { useAppNavSection } from './useAppNavSection'

type AppNavLinkProps = {
  to: string
  section: AppNavSection
  activeSection: AppNavSection | undefined
  children: ReactNode
}

function AppNavLink({ to, section, activeSection, children }: AppNavLinkProps) {
  const active = activeSection === section

  return (
    <Link
      to={to}
      className={navLinkClassName(active)}
      aria-current={active ? 'page' : undefined}
    >
      {children}
    </Link>
  )
}

export function AppShell() {
  const intl = useIntl()
  const activeSection = useAppNavSection()

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
          <AppNavLink to="/" section="explore" activeSection={activeSection}>
            <FormattedMessage id="nav.exploreRoutes" />
          </AppNavLink>
          <AppNavLink
            to={`/routes/${DEMO_PUBLISHED_ROUTE_ID}`}
            section="routeDetail"
            activeSection={activeSection}
          >
            <FormattedMessage id="nav.routeDetail" />
          </AppNavLink>
          <AppNavLink
            to="/plan"
            section="tripPlanner"
            activeSection={activeSection}
          >
            <FormattedMessage id="nav.tripPlanner" />
          </AppNavLink>
          <AppNavLink to="/trips" section="myTrips" activeSection={activeSection}>
            <FormattedMessage id="nav.myTrips" />
          </AppNavLink>
          <AppNavLink
            to="/review"
            section="routeWiki"
            activeSection={activeSection}
          >
            <FormattedMessage id="nav.routeWiki" />
          </AppNavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}

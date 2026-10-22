import { FormattedMessage, useIntl } from 'react-intl'
import { ExploreFilters } from '../features/explore/ExploreFilters'
import { ExploreRouteMap } from '../features/explore/ExploreRouteMap'
import { RouteListRow } from '../features/explore/RouteListRow'
import { useExploreRoutes } from '../features/explore/useExploreRoutes'

export function ExploreRoutesPage() {
  const intl = useIntl()
  const {
    routes,
    status,
    routeType,
    setRouteType,
    seasonMonth,
    setSeasonMonth,
  } = useExploreRoutes()

  const mapRoutes = status === 'ready' || status === 'empty' ? routes : []

  return (
    <main className="explore-page">
      <div className="explore-layout">
        <section
          className="explore-list-panel"
          aria-labelledby="explore-heading"
        >
          <ExploreFilters
            routeType={routeType}
            seasonMonth={seasonMonth}
            onRouteTypeChange={setRouteType}
            onSeasonMonthChange={setSeasonMonth}
          />
          <div className="explore-list-body">
            {status === 'loading' ? (
              <p className="explore-status" role="status">
                <FormattedMessage id="explore.status.loading" />
              </p>
            ) : null}
            {status === 'error' ? (
              <p className="explore-status explore-status-error" role="alert">
                <FormattedMessage id="explore.status.error" />
              </p>
            ) : null}
            {status === 'empty' ? (
              <p className="explore-status" role="status">
                <FormattedMessage id="explore.status.empty" />
              </p>
            ) : null}
            {status === 'ready' ? (
              <ul className="explore-route-list">
                {routes.map((route) => (
                  <RouteListRow key={route.id} route={route} />
                ))}
              </ul>
            ) : null}
          </div>
        </section>
        <section
          className="explore-map-panel"
          aria-label={intl.formatMessage({ id: 'explore.map.ariaLabel' })}
        >
          <ExploreRouteMap routes={mapRoutes} />
        </section>
      </div>
    </main>
  )
}

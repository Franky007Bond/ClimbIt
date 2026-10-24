import { FormattedMessage, useIntl } from 'react-intl'
import { Link } from 'react-router-dom'
import type { RouteDetail } from '../../api/generated/types.gen'
import { RouteStateMeta } from '../routes/RouteStateMeta'
import { enumMessageId } from '../explore/enumLabels'
import {
  formatDifficultyScale,
  normalizedDifficultyGrade,
} from './difficultyDisplay'
import { ElevationProfileChart } from './ElevationProfileChart'
import { RouteDetailMap } from './RouteDetailMap'

type RouteDetailContentProps = {
  route: RouteDetail
}

function formatCoordinate(value: number): string {
  return value.toFixed(5)
}

export function RouteDetailContent({ route }: RouteDetailContentProps) {
  const intl = useIntl()

  return (
    <div className="route-detail-layout">
      <section
        className="route-detail-info"
        aria-labelledby="route-detail-heading"
      >
        <header className="route-detail-header">
          <h1 id="route-detail-heading" className="route-detail-name">
            {route.name}
          </h1>
          <p className="route-detail-type">
            {intl.formatMessage({
              id: enumMessageId('enum.routeType', route.route_type),
            })}
          </p>
          <p className="route-detail-region">
            <span className="route-detail-region-label">
              <FormattedMessage id="routeDetail.field.region" />
              {': '}
            </span>
            <FormattedMessage
              id="routeDetail.region.value"
              values={{
                name: route.region.name,
                country: route.region.country,
              }}
            />
          </p>
        </header>

        <RouteStateMeta route={route} />

        <section
          className="route-detail-section"
          aria-labelledby="route-detail-difficulty-heading"
        >
          <h2
            id="route-detail-difficulty-heading"
            className="route-detail-section-title"
          >
            <FormattedMessage id="routeDetail.section.difficulty" />
          </h2>
          {route.difficulty ? (
            <dl className="route-detail-dl">
              <div className="route-detail-dl-row">
                <dt>
                  <FormattedMessage id="routeDetail.difficulty.normalized" />
                </dt>
                <dd>{normalizedDifficultyGrade(route.difficulty)}</dd>
              </div>
              {route.difficulty.original_value ? (
                <div className="route-detail-dl-row">
                  <dt>
                    <FormattedMessage id="routeDetail.difficulty.originalValue" />
                  </dt>
                  <dd>{route.difficulty.original_value}</dd>
                </div>
              ) : null}
              {route.difficulty.original_scale ? (
                <div className="route-detail-dl-row">
                  <dt>
                    <FormattedMessage id="routeDetail.difficulty.originalScale" />
                  </dt>
                  <dd>
                    {formatDifficultyScale(
                      intl,
                      route.difficulty.original_scale,
                    )}
                  </dd>
                </div>
              ) : null}
            </dl>
          ) : (
            <p className="route-detail-muted">
              <FormattedMessage id="routeDetail.difficulty.missing" />
            </p>
          )}
        </section>

        {route.elevation_profile ? (
          <ElevationProfileChart profile={route.elevation_profile} />
        ) : null}

        {route.trailhead_transit_connection ? (
          <section
            className="route-detail-section"
            aria-labelledby="route-detail-transit-heading"
          >
            <h2
              id="route-detail-transit-heading"
              className="route-detail-section-title"
            >
              <FormattedMessage id="routeDetail.section.transitConnection" />
            </h2>
            <dl className="route-detail-dl">
              <div className="route-detail-dl-row">
                <dt>
                  <FormattedMessage id="routeDetail.transit.stopName" />
                </dt>
                <dd>{route.trailhead_transit_connection.stop_name}</dd>
              </div>
              <div className="route-detail-dl-row">
                <dt>
                  <FormattedMessage id="routeDetail.transit.distance" />
                </dt>
                <dd>
                  <FormattedMessage
                    id="routeDetail.transit.distanceKm"
                    values={{
                      km: (
                        route.trailhead_transit_connection.distance_m / 1000
                      ).toFixed(1),
                    }}
                  />
                </dd>
              </div>
            </dl>
          </section>
        ) : null}

        <section
          className="route-detail-section"
          aria-labelledby="route-detail-trailhead-heading"
        >
          <h2
            id="route-detail-trailhead-heading"
            className="route-detail-section-title"
          >
            <FormattedMessage id="routeDetail.section.trailhead" />
          </h2>
          {route.trailhead ? (
            <dl className="route-detail-dl">
              <div className="route-detail-dl-row">
                <dt>
                  <FormattedMessage id="routeDetail.trailhead.latitude" />
                </dt>
                <dd>{formatCoordinate(route.trailhead.latitude)}</dd>
              </div>
              <div className="route-detail-dl-row">
                <dt>
                  <FormattedMessage id="routeDetail.trailhead.longitude" />
                </dt>
                <dd>{formatCoordinate(route.trailhead.longitude)}</dd>
              </div>
            </dl>
          ) : (
            <p className="route-detail-muted">
              <FormattedMessage id="routeDetail.trailhead.missing" />
            </p>
          )}
        </section>

        {route.description.trim().length > 0 ? (
          <section
            className="route-detail-section"
            aria-labelledby="route-detail-description-heading"
          >
            <h2
              id="route-detail-description-heading"
              className="route-detail-section-title"
            >
              <FormattedMessage id="routeDetail.section.description" />
            </h2>
            <p className="route-detail-description">{route.description}</p>
          </section>
        ) : null}

        <p className="route-detail-actions">
          <Link
            to={`/plan?routeId=${encodeURIComponent(route.id)}`}
            className="route-detail-plan-link"
          >
            <FormattedMessage id="routeDetail.plan.action" />
          </Link>
        </p>
      </section>

      <section
        className="route-detail-map-panel"
        aria-label={intl.formatMessage({ id: 'routeDetail.map.ariaLabel' })}
      >
        <RouteDetailMap
          linestring={route.linestring}
          trailhead={route.trailhead}
          trailheadTransitConnection={route.trailhead_transit_connection}
        />
      </section>
    </div>
  )
}

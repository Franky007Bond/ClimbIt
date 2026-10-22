import { FormattedMessage, useIntl } from 'react-intl'
import type { RouteType } from '../../api/generated/types.gen'
import type { MessageKey } from '../../i18n/messages'
import type { RouteTypeFilter, SeasonMonthFilter } from './useExploreRoutes'

const ROUTE_TYPES: RouteType[] = [
  'klettersteig',
  'alpine_hike',
  'outdoor_climbing',
]

const SEASON_MONTHS = Array.from({ length: 12 }, (_, index) => index + 1)

type ExploreFiltersProps = {
  routeType: RouteTypeFilter
  seasonMonth: SeasonMonthFilter
  onRouteTypeChange: (value: RouteTypeFilter) => void
  onSeasonMonthChange: (value: SeasonMonthFilter) => void
}

export function ExploreFilters({
  routeType,
  seasonMonth,
  onRouteTypeChange,
  onSeasonMonthChange,
}: ExploreFiltersProps) {
  const intl = useIntl()

  return (
    <div className="explore-filters">
      <h1 id="explore-heading" className="explore-heading">
        <FormattedMessage id="page.exploreRoutes.title" />
      </h1>
      <div className="explore-filter-row">
        <label className="explore-filter-label">
          <span>
            <FormattedMessage id="explore.filter.routeType.label" />
          </span>
          <select
            aria-label={intl.formatMessage({
              id: 'explore.filter.routeType.label',
            })}
            className="explore-filter-control"
            value={routeType}
            onChange={(event) => {
              onRouteTypeChange(event.target.value as RouteTypeFilter)
            }}
          >
            <option value="">
              {intl.formatMessage({ id: 'explore.filter.routeType.all' })}
            </option>
            {ROUTE_TYPES.map((type) => (
              <option key={type} value={type}>
                {intl.formatMessage({ id: `enum.routeType.${type}` })}
              </option>
            ))}
          </select>
        </label>
        <label className="explore-filter-label">
          <span>
            <FormattedMessage id="explore.filter.season.label" />
          </span>
          <select
            aria-label={intl.formatMessage({ id: 'explore.filter.season.label' })}
            className="explore-filter-control"
            value={seasonMonth === '' ? '' : String(seasonMonth)}
            onChange={(event) => {
              const value = event.target.value
              onSeasonMonthChange(value === '' ? '' : Number(value))
            }}
          >
            <option value="">
              {intl.formatMessage({ id: 'explore.filter.season.all' })}
            </option>
            {SEASON_MONTHS.map((month) => (
              <option key={month} value={month}>
                {intl.formatMessage({
                  id: `explore.filter.season.month.${month}` as MessageKey,
                })}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  )
}

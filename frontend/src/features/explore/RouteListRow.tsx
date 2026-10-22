import { useIntl } from 'react-intl'
import { Link } from 'react-router-dom'
import type { RouteSearchItem } from '../../api/generated/types.gen'
import { RouteStateMeta } from '../routes/RouteStateMeta'
import { enumMessageId } from './enumLabels'

type RouteListRowProps = {
  route: RouteSearchItem
}

export function RouteListRow({ route }: RouteListRowProps) {
  const intl = useIntl()

  return (
    <li className="explore-route-row">
      <h2 className="explore-route-name">
        <Link to={`/routes/${route.id}`} className="explore-route-name-link">
          {route.name}
        </Link>
      </h2>
      <p className="explore-route-type">
        {intl.formatMessage({
          id: enumMessageId('enum.routeType', route.route_type),
        })}
      </p>
      <RouteStateMeta route={route} />
    </li>
  )
}

import { FormattedMessage, useIntl } from 'react-intl'
import type { RouteSearchItem } from '../../api/generated/types.gen'
import type { MessageKey } from '../../i18n/messages'
import { enumMessageId } from './enumLabels'

type RouteListRowProps = {
  route: RouteSearchItem
}

function StateField({
  labelId,
  valueId,
}: {
  labelId: MessageKey
  valueId: MessageKey
}) {
  return (
    <div className="explore-route-field">
      <dt>
        <FormattedMessage id={labelId} />
      </dt>
      <dd>
        <FormattedMessage id={valueId} />
      </dd>
    </div>
  )
}

export function RouteListRow({ route }: RouteListRowProps) {
  const intl = useIntl()

  return (
    <li className="explore-route-row">
      <h2 className="explore-route-name">{route.name}</h2>
      <p className="explore-route-type">
        {intl.formatMessage({
          id: enumMessageId('enum.routeType', route.route_type),
        })}
      </p>
      <dl className="explore-route-meta">
        <StateField
          labelId="explore.route.field.publication"
          valueId={enumMessageId('enum.publication', route.publication)}
        />
        <StateField
          labelId="explore.route.field.provenance"
          valueId={enumMessageId('enum.provenance', route.provenance)}
        />
        <StateField
          labelId="explore.route.field.completeness"
          valueId={enumMessageId('enum.completeness', route.completeness)}
        />
        <StateField
          labelId="explore.route.field.assessment"
          valueId={enumMessageId('enum.assessment', route.assessment)}
        />
        <StateField
          labelId="explore.route.field.regionCoverage"
          valueId={enumMessageId('enum.regionCoverage', route.region.coverage)}
        />
      </dl>
    </li>
  )
}

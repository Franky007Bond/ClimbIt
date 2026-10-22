import { FormattedMessage } from 'react-intl'
import type { MessageKey } from '../../i18n/messages'

type RouteStateFieldProps = {
  labelId: MessageKey
  valueId: MessageKey
}

export function RouteStateField({ labelId, valueId }: RouteStateFieldProps) {
  return (
    <div className="route-state-field">
      <dt>
        <FormattedMessage id={labelId} />
      </dt>
      <dd>
        <FormattedMessage id={valueId} />
      </dd>
    </div>
  )
}

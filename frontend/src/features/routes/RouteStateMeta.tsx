import type { RouteSearchItem } from '../../api/generated/types.gen'
import { enumMessageId } from '../explore/enumLabels'
import { RouteStateField } from './RouteStateField'

type RouteStateMetaProps = {
  route: Pick<
    RouteSearchItem,
    'publication' | 'provenance' | 'completeness' | 'assessment' | 'region'
  >
}

export function RouteStateMeta({ route }: RouteStateMetaProps) {
  return (
    <dl className="route-state-meta">
      <RouteStateField
        labelId="explore.route.field.publication"
        valueId={enumMessageId('enum.publication', route.publication)}
      />
      <RouteStateField
        labelId="explore.route.field.provenance"
        valueId={enumMessageId('enum.provenance', route.provenance)}
      />
      <RouteStateField
        labelId="explore.route.field.completeness"
        valueId={enumMessageId('enum.completeness', route.completeness)}
      />
      <RouteStateField
        labelId="explore.route.field.assessment"
        valueId={enumMessageId('enum.assessment', route.assessment)}
      />
      <RouteStateField
        labelId="explore.route.field.regionCoverage"
        valueId={enumMessageId('enum.regionCoverage', route.region.coverage)}
      />
    </dl>
  )
}

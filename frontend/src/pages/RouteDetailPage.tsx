import { useParams } from 'react-router-dom'
import { PlaceholderPage } from '../components/PlaceholderPage'

export function RouteDetailPage() {
  const { routeId } = useParams<{ routeId: string }>()
  const resolvedRouteId = routeId ?? ''

  return (
    <PlaceholderPage
      titleId="page.routeDetail.title"
      bodyId="page.routeDetail.body"
      bodyValues={{ routeId: resolvedRouteId }}
    />
  )
}

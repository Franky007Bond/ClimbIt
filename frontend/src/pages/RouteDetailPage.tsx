import { FormattedMessage } from 'react-intl'
import { useParams } from 'react-router-dom'
import { RouteDetailContent } from '../features/route-detail/RouteDetailContent'
import { useRouteDetail } from '../features/route-detail/useRouteDetail'

export function RouteDetailPage() {
  const { routeId } = useParams<{ routeId: string }>()
  const { route, status } = useRouteDetail(routeId)

  return (
    <main className="route-detail-page">
      {status === 'loading' ? (
        <p className="route-detail-status" role="status">
          <FormattedMessage id="routeDetail.status.loading" />
        </p>
      ) : null}
      {status === 'notFound' ? (
        <p className="route-detail-status route-detail-status-error" role="alert">
          <FormattedMessage id="routeDetail.status.notFound" />
        </p>
      ) : null}
      {status === 'error' ? (
        <p className="route-detail-status route-detail-status-error" role="alert">
          <FormattedMessage id="routeDetail.status.error" />
        </p>
      ) : null}
      {status === 'ready' && route ? (
        <RouteDetailContent route={route} />
      ) : null}
    </main>
  )
}

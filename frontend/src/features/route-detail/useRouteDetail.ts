import { useEffect, useState } from 'react'
import { getRouteDetailRoutesRouteIdGet } from '../../api/generated/sdk.gen'
import type { RouteDetail } from '../../api/generated/types.gen'

export type RouteDetailLoadStatus = 'loading' | 'ready' | 'notFound' | 'error'

export function useRouteDetail(routeId: string | undefined) {
  const [route, setRoute] = useState<RouteDetail | null>(null)
  const [status, setStatus] = useState<RouteDetailLoadStatus>('loading')

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!routeId) {
        setRoute(null)
        setStatus('error')
        return
      }

      setStatus('loading')
      setRoute(null)

      const result = await getRouteDetailRoutesRouteIdGet({
        path: { route_id: routeId },
        throwOnError: false,
      })

      if (cancelled) {
        return
      }

      if (
        result.response.status === 404 ||
        result.response.status === 422
      ) {
        setRoute(null)
        setStatus('notFound')
        return
      }

      if (result.error || !result.response.ok || !result.data) {
        setRoute(null)
        setStatus('error')
        return
      }

      setRoute(result.data)
      setStatus('ready')
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [routeId])

  return { route, status }
}

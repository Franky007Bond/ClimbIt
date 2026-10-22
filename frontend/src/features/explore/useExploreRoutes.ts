import { useEffect, useState } from 'react'
import { listRoutesRoutesGet } from '../../api/generated/sdk.gen'
import type { RouteSearchItem, RouteType } from '../../api/generated/types.gen'

export type ExploreLoadStatus = 'loading' | 'ready' | 'empty' | 'error'

export type RouteTypeFilter = RouteType | ''
export type SeasonMonthFilter = number | ''

export function useExploreRoutes() {
  const [routeType, setRouteType] = useState<RouteTypeFilter>('')
  const [seasonMonth, setSeasonMonth] = useState<SeasonMonthFilter>('')
  const [routes, setRoutes] = useState<RouteSearchItem[]>([])
  const [status, setStatus] = useState<ExploreLoadStatus>('loading')

  useEffect(() => {
    let cancelled = false

    async function load() {
      setStatus('loading')
      const result = await listRoutesRoutesGet({
        query: {
          ...(routeType ? { route_type: routeType } : {}),
          ...(seasonMonth ? { season_month: seasonMonth } : {}),
        },
        throwOnError: false,
      })

      if (cancelled) {
        return
      }

      if (result.error || !result.response.ok) {
        setRoutes([])
        setStatus('error')
        return
      }

      const list = result.data?.routes ?? []
      setRoutes(list)
      setStatus(list.length === 0 ? 'empty' : 'ready')
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [routeType, seasonMonth])

  return {
    routes,
    status,
    routeType,
    setRouteType,
    seasonMonth,
    setSeasonMonth,
  }
}

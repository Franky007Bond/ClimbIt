import { useEffect } from 'react'
import { CircleMarker, useMap } from 'react-leaflet'
import type { RouteSearchItem } from '../../api/generated/types.gen'
import { ClimbItMapContainer } from '../map/ClimbItMapContainer'
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM } from '../map/mapConstants'

type ExploreRouteMapProps = {
  routes: RouteSearchItem[]
}

function FitMapToRoutes({ routes }: { routes: RouteSearchItem[] }) {
  const map = useMap()

  useEffect(() => {
    if (routes.length === 0) {
      map.setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)
      return
    }
    if (routes.length === 1) {
      const only = routes[0]!.trailhead
      map.setView([only.latitude, only.longitude], 11)
      return
    }
    const bounds = routes.map(
      (route) =>
        [route.trailhead.latitude, route.trailhead.longitude] as [
          number,
          number,
        ],
    )
    map.fitBounds(bounds, { padding: [32, 32] })
  }, [map, routes])

  return null
}

export function ExploreRouteMap({ routes }: ExploreRouteMapProps) {
  return (
    <ClimbItMapContainer className="explore-map" scrollWheelZoom>
      <FitMapToRoutes routes={routes} />
      {routes.map((route) => (
        <CircleMarker
          key={route.id}
          center={[route.trailhead.latitude, route.trailhead.longitude]}
          radius={8}
          pathOptions={{ color: '#2563eb', fillColor: '#2563eb', fillOpacity: 0.85 }}
        />
      ))}
    </ClimbItMapContainer>
  )
}

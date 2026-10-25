import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CircleMarker, Tooltip, useMap } from 'react-leaflet'
import type { RouteSearchItem } from '../../api/generated/types.gen'
import { ClimbItMapContainer } from '../map/ClimbItMapContainer'
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM } from '../map/mapConstants'

const ROUTE_MARKER_HIT_RADIUS = 22
const ROUTE_MARKER_VISIBLE_RADIUS = 8

const ROUTE_MARKER_VISIBLE_STYLE = {
  color: '#2563eb',
  fillColor: '#2563eb',
  fillOpacity: 0.85,
  className: 'explore-route-marker-dot',
} as const

const ROUTE_MARKER_HIT_STYLE = {
  fillOpacity: 0,
  opacity: 0,
  stroke: false,
  className: 'explore-route-marker-hit',
} as const

function ExploreRouteMarker({ route }: { route: RouteSearchItem }) {
  const navigate = useNavigate()

  const openRoute = () => {
    navigate(`/routes/${route.id}`)
  }

  return (
    <>
      <CircleMarker
        center={[route.trailhead.latitude, route.trailhead.longitude]}
        radius={ROUTE_MARKER_HIT_RADIUS}
        pathOptions={ROUTE_MARKER_HIT_STYLE}
        eventHandlers={{
          click: openRoute,
        }}
      >
        <Tooltip direction="top" offset={[0, -4]} opacity={0.95}>
          {route.name}
        </Tooltip>
      </CircleMarker>
      <CircleMarker
        center={[route.trailhead.latitude, route.trailhead.longitude]}
        radius={ROUTE_MARKER_VISIBLE_RADIUS}
        pathOptions={ROUTE_MARKER_VISIBLE_STYLE}
        interactive={false}
      />
    </>
  )
}

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
        <ExploreRouteMarker key={route.id} route={route} />
      ))}
    </ClimbItMapContainer>
  )
}

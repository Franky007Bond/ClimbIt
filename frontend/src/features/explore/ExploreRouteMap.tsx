import { useEffect } from 'react'
import { CircleMarker, MapContainer, TileLayer, useMap } from 'react-leaflet'
import type { RouteSearchItem } from '../../api/generated/types.gen'
import 'leaflet/dist/leaflet.css'

const DEFAULT_CENTER: [number, number] = [47.2, 10.5]
const DEFAULT_ZOOM = 6

type ExploreRouteMapProps = {
  routes: RouteSearchItem[]
}

function FitMapToRoutes({ routes }: { routes: RouteSearchItem[] }) {
  const map = useMap()

  useEffect(() => {
    if (routes.length === 0) {
      map.setView(DEFAULT_CENTER, DEFAULT_ZOOM)
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
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      className="explore-map"
      scrollWheelZoom
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      <FitMapToRoutes routes={routes} />
      {routes.map((route) => (
        <CircleMarker
          key={route.id}
          center={[route.trailhead.latitude, route.trailhead.longitude]}
          radius={8}
          pathOptions={{ color: '#2563eb', fillColor: '#2563eb', fillOpacity: 0.85 }}
        />
      ))}
    </MapContainer>
  )
}

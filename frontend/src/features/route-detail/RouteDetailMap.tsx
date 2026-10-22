import { useEffect } from 'react'
import { CircleMarker, Polyline, useMap } from 'react-leaflet'
import type { LineString, Point } from '../../api/generated/types.gen'
import { ClimbItMapContainer } from '../map/ClimbItMapContainer'
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM } from '../map/mapConstants'

type RouteDetailMapProps = {
  linestring: LineString | null
  trailhead: Point | null
}

function toLatLng(point: Point): [number, number] {
  return [point.latitude, point.longitude]
}

function FitMapToRoute({
  linestring,
  trailhead,
}: {
  linestring: LineString | null
  trailhead: Point | null
}) {
  const map = useMap()

  useEffect(() => {
    const points = linestring?.points ?? []
    if (points.length >= 2) {
      map.fitBounds(points.map(toLatLng), { padding: [32, 32] })
      return
    }
    if (trailhead) {
      map.setView(toLatLng(trailhead), 13)
      return
    }
    map.setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)
  }, [map, linestring, trailhead])

  return null
}

export function RouteDetailMap({ linestring, trailhead }: RouteDetailMapProps) {
  const points = linestring?.points ?? []
  const polylinePositions =
    points.length >= 2 ? points.map(toLatLng) : null

  return (
    <ClimbItMapContainer className="route-detail-map" scrollWheelZoom>
      <FitMapToRoute linestring={linestring} trailhead={trailhead} />
      {polylinePositions ? (
        <Polyline
          positions={polylinePositions}
          pathOptions={{ color: '#2563eb', weight: 4 }}
        />
      ) : null}
      {trailhead ? (
        <CircleMarker
          center={toLatLng(trailhead)}
          radius={8}
          pathOptions={{
            color: '#2563eb',
            fillColor: '#2563eb',
            fillOpacity: 0.85,
          }}
        />
      ) : null}
    </ClimbItMapContainer>
  )
}

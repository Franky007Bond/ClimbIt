import { useEffect } from 'react'
import { CircleMarker, Polyline, useMap } from 'react-leaflet'
import type {
  LineString,
  Point,
  TrailheadTransitConnection,
} from '../../api/generated/types.gen'
import { ClimbItMapContainer } from '../map/ClimbItMapContainer'
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM } from '../map/mapConstants'

type RouteDetailMapProps = {
  linestring: LineString | null
  trailhead: Point | null
  trailheadTransitConnection: TrailheadTransitConnection | null
}

function toLatLng(point: Point): [number, number] {
  return [point.latitude, point.longitude]
}

function FitMapToRoute({
  linestring,
  trailhead,
  trailheadTransitConnection,
}: {
  linestring: LineString | null
  trailhead: Point | null
  trailheadTransitConnection: TrailheadTransitConnection | null
}) {
  const map = useMap()

  useEffect(() => {
    const points = linestring?.points ?? []
    const boundsPoints = [...points]
    if (trailhead) {
      boundsPoints.push(trailhead)
    }
    if (trailheadTransitConnection) {
      boundsPoints.push({
        latitude: trailheadTransitConnection.latitude,
        longitude: trailheadTransitConnection.longitude,
      })
    }
    if (boundsPoints.length >= 2) {
      map.fitBounds(boundsPoints.map(toLatLng), { padding: [32, 32] })
      return
    }
    if (trailhead) {
      map.setView(toLatLng(trailhead), 13)
      return
    }
    map.setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)
  }, [map, linestring, trailhead, trailheadTransitConnection])

  return null
}

export function RouteDetailMap({
  linestring,
  trailhead,
  trailheadTransitConnection,
}: RouteDetailMapProps) {
  const points = linestring?.points ?? []
  const polylinePositions =
    points.length >= 2 ? points.map(toLatLng) : null

  return (
    <ClimbItMapContainer className="route-detail-map" scrollWheelZoom>
      <FitMapToRoute
        linestring={linestring}
        trailhead={trailhead}
        trailheadTransitConnection={trailheadTransitConnection}
      />
      {polylinePositions ? (
        <Polyline
          positions={polylinePositions}
          pathOptions={{ color: '#2563eb', weight: 4 }}
        />
      ) : null}
      {trailheadTransitConnection ? (
        <Polyline
          positions={[
            [
              trailheadTransitConnection.latitude,
              trailheadTransitConnection.longitude,
            ],
            ...(trailhead ? [toLatLng(trailhead)] : []),
          ]}
          pathOptions={{ color: '#f59e0b', weight: 3, dashArray: '6 8' }}
        />
      ) : null}
      {trailheadTransitConnection ? (
        <CircleMarker
          center={[
            trailheadTransitConnection.latitude,
            trailheadTransitConnection.longitude,
          ]}
          radius={7}
          pathOptions={{
            color: '#f59e0b',
            fillColor: '#fbbf24',
            fillOpacity: 0.9,
          }}
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

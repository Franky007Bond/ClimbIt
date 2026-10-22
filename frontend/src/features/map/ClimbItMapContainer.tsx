import type { ReactNode } from 'react'
import { MapContainer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM } from './mapConstants'
import { OsmTileLayer } from './OsmTileLayer'

type ClimbItMapContainerProps = {
  className?: string
  scrollWheelZoom?: boolean
  children: ReactNode
}

export function ClimbItMapContainer({
  className,
  scrollWheelZoom = true,
  children,
}: ClimbItMapContainerProps) {
  return (
    <MapContainer
      center={DEFAULT_MAP_CENTER}
      zoom={DEFAULT_MAP_ZOOM}
      className={className}
      scrollWheelZoom={scrollWheelZoom}
    >
      <OsmTileLayer />
      {children}
    </MapContainer>
  )
}

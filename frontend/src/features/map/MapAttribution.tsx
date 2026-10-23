import { MAP_TILE_ATTRIBUTION } from './mapConfig'

export function MapAttribution() {
  return (
    <div
      className="map-attribution"
      data-testid="map-attribution"
      dangerouslySetInnerHTML={{ __html: MAP_TILE_ATTRIBUTION }}
    />
  )
}

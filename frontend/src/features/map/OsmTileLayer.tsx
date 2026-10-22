import { TileLayer } from 'react-leaflet'
import { OSM_TILE_ATTRIBUTION, OSM_TILE_URL } from './mapConstants'

export function OsmTileLayer() {
  return (
    <TileLayer url={OSM_TILE_URL} attribution={OSM_TILE_ATTRIBUTION} />
  )
}

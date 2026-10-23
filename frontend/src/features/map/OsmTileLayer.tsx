import { TileLayer } from 'react-leaflet'
import { MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from './mapConfig'

export function OsmTileLayer() {
  return (
    <TileLayer url={MAP_TILE_URL} attribution={MAP_TILE_ATTRIBUTION} />
  )
}

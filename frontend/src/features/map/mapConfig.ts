const defaultTileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const defaultAttribution =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

export const MAP_TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL?.trim() || defaultTileUrl

export const MAP_TILE_ATTRIBUTION =
  import.meta.env.VITE_MAP_TILE_ATTRIBUTION?.trim() || defaultAttribution

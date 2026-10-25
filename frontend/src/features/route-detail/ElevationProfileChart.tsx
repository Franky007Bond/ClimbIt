import { useId } from 'react'
import { FormattedMessage, useIntl } from 'react-intl'
import type { ElevationProfile } from '../../api/generated/types.gen'

type ElevationProfileChartProps = {
  profile: ElevationProfile
}

const WIDTH = 640
const HEIGHT = 160
const PAD = { top: 12, right: 12, bottom: 28, left: 44 }

export function ElevationProfileChart({ profile }: ElevationProfileChartProps) {
  const intl = useIntl()
  const gradientId = useId()
  const points = profile.points
  if (points.length < 2) {
    return null
  }

  const maxDistance = points[points.length - 1]?.distance_m ?? 0
  const elevations = points.map((point) => point.elevation_m)
  const minElev = Math.min(...elevations)
  const maxElev = Math.max(...elevations)
  const elevSpan = Math.max(maxElev - minElev, 1)

  const plotWidth = WIDTH - PAD.left - PAD.right
  const plotHeight = HEIGHT - PAD.top - PAD.bottom

  const toX = (distanceM: number) =>
    PAD.left + (maxDistance > 0 ? (distanceM / maxDistance) * plotWidth : 0)
  const toY = (elevationM: number) =>
    PAD.top + plotHeight - ((elevationM - minElev) / elevSpan) * plotHeight

  const linePoints = points.map((point) => `${toX(point.distance_m)},${toY(point.elevation_m)}`)
  const areaPoints = [
    `${toX(points[0].distance_m)},${toY(minElev)}`,
    ...linePoints,
    `${toX(points[points.length - 1].distance_m)},${toY(minElev)}`,
  ].join(' ')

  const ariaLabel = intl.formatMessage(
    { id: 'routeDetail.elevationProfile.ariaLabel' },
    { min: minElev, max: maxElev },
  )

  return (
    <figure className="route-detail-elevation">
      <figcaption className="route-detail-section-title">
        <FormattedMessage id="routeDetail.section.elevationProfile" />
      </figcaption>
      {profile.synthesized ? (
        <p className="route-detail-elevation-note">
          <FormattedMessage id="routeDetail.elevationProfile.synthesized" />
        </p>
      ) : (
        <p className="route-detail-elevation-note">
          <FormattedMessage id="routeDetail.elevationProfile.fromGpx" />
        </p>
      )}
      <svg
        className="route-detail-elevation-chart"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={ariaLabel}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#4edea3" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#4edea3" stopOpacity="0.05" />
          </linearGradient>
        </defs>
        <polygon fill={`url(#${gradientId})`} points={areaPoints} />
        <polyline
          fill="none"
          stroke="#2563eb"
          strokeWidth={2.5}
          points={linePoints.join(' ')}
        />
        <text
          x={PAD.left}
          y={HEIGHT - 6}
          className="route-detail-elevation-axis"
          textAnchor="start"
        >
          0 m
        </text>
        <text
          x={WIDTH - PAD.right}
          y={HEIGHT - 6}
          className="route-detail-elevation-axis"
          textAnchor="end"
        >
          {intl.formatMessage(
            { id: 'routeDetail.elevationProfile.distanceKm' },
            { km: (maxDistance / 1000).toFixed(1) },
          )}
        </text>
        <text
          x={8}
          y={PAD.top + 4}
          className="route-detail-elevation-axis"
          textAnchor="start"
        >
          {maxElev} m
        </text>
        <text
          x={8}
          y={PAD.top + plotHeight}
          className="route-detail-elevation-axis"
          textAnchor="start"
        >
          {minElev} m
        </text>
      </svg>
    </figure>
  )
}

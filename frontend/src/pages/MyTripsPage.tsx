import { useCallback, useEffect, useState } from 'react'
import { FormattedMessage } from 'react-intl'
import { Link } from 'react-router-dom'
import {
  createTripShareLinkTripsTripIdSharePost,
  deleteTripTripsTripIdDelete,
  ensureTripCapabilityTripsCapabilityGet,
  getTripTripsTripIdGet,
  listTripsTripsGet,
  reevaluateTripTripsTripIdReevaluatePost,
} from '../api/generated/sdk.gen'
import type { TripDetailResponse, TripListItem } from '../api/generated/types.gen'
import '../api/client'
import { recommendationClass } from '../features/trips/recommendationClass'
export function MyTripsPage() {
  const [trips, setTrips] = useState<TripListItem[]>([])
  const [selectedTripId, setSelectedTripId] = useState<string | null>(null)
  const [detail, setDetail] = useState<TripDetailResponse | null>(null)
  const [statusMessageId, setStatusMessageId] = useState<string | null>(null)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyTripId, setBusyTripId] = useState<string | null>(null)

  const refreshTrips = useCallback(async () => {
    setLoading(true)
    await ensureTripCapabilityTripsCapabilityGet({ throwOnError: false })
    const listed = await listTripsTripsGet({ throwOnError: false })
    setLoading(false)
    if (!listed.response.ok || !listed.data) {
      setStatusMessageId('myTrips.status.error')
      setTrips([])
      return
    }
    setTrips(listed.data.trips)
  }, [])

  useEffect(() => {
    void refreshTrips()
  }, [refreshTrips])

  async function loadDetail(tripId: string) {
    setSelectedTripId(tripId)
    setShareUrl(null)
    const result = await getTripTripsTripIdGet({
      path: { trip_id: tripId },
      throwOnError: false,
    })
    if (!result.response.ok || !result.data) {
      setDetail(null)
      setStatusMessageId('myTrips.status.error')
      return
    }
    setDetail(result.data)
  }

  async function onReevaluate(tripId: string) {
    setBusyTripId(tripId)
    setStatusMessageId(null)
    const result = await reevaluateTripTripsTripIdReevaluatePost({
      path: { trip_id: tripId },
      throwOnError: false,
    })
    setBusyTripId(null)
    if (!result.response.ok || !result.data) {
      setStatusMessageId('myTrips.status.error')
      return
    }
    setDetail(result.data)
    await refreshTrips()
    setStatusMessageId('myTrips.status.reevaluated')
  }

  async function onDelete(tripId: string) {
    setBusyTripId(tripId)
    const result = await deleteTripTripsTripIdDelete({
      path: { trip_id: tripId },
      throwOnError: false,
    })
    setBusyTripId(null)
    if (!result.response.ok) {
      setStatusMessageId('myTrips.status.error')
      return
    }
    if (selectedTripId === tripId) {
      setSelectedTripId(null)
      setDetail(null)
      setShareUrl(null)
    }
    await refreshTrips()
    setStatusMessageId('myTrips.status.deleted')
  }

  async function onShare(tripId: string) {
    setBusyTripId(tripId)
    const result = await createTripShareLinkTripsTripIdSharePost({
      path: { trip_id: tripId },
      throwOnError: false,
    })
    setBusyTripId(null)
    if (!result.response.ok || !result.data) {
      setStatusMessageId('myTrips.status.error')
      return
    }
    const url = `${window.location.origin}/share/${result.data.share_token}`
    setShareUrl(url)
    setStatusMessageId('myTrips.status.shareReady')
  }

  return (
    <section className="my-trips" aria-labelledby="my-trips-heading">
      <header className="my-trips-header">
        <h1 id="my-trips-heading">
          <FormattedMessage id="page.myTrips.title" />
        </h1>
        <p className="my-trips-lead">
          <FormattedMessage id="myTrips.lead" />
        </p>
      </header>

      {statusMessageId ? (
        <p className="my-trips-status" role="status">
          <FormattedMessage id={statusMessageId} />
        </p>
      ) : null}

      {shareUrl ? (
        <p className="my-trips-share-url">
          <FormattedMessage id="myTrips.share.urlLabel" />{' '}
          <Link to={shareUrl.replace(window.location.origin, '')}>{shareUrl}</Link>
        </p>
      ) : null}

      {loading ? (
        <p>
          <FormattedMessage id="myTrips.status.loading" />
        </p>
      ) : trips.length === 0 ? (
        <p>
          <FormattedMessage id="myTrips.status.empty" />
        </p>
      ) : (
        <ul className="my-trips-list">
          {trips.map((trip) => (
            <li key={trip.trip_id} className="my-trips-card">
              <div className="my-trips-card-main">
                <p className="my-trips-card-date">{trip.plan_date}</p>
                <p className="my-trips-card-route">{trip.route_id}</p>
                <span className={recommendationClass(trip.recommendation)} role="status">
                  {trip.recommendation}
                </span>
              </div>
              <div className="my-trips-actions">
                <button type="button" onClick={() => void loadDetail(trip.trip_id)}>
                  <FormattedMessage id="myTrips.action.view" />
                </button>
                <button
                  type="button"
                  disabled={busyTripId === trip.trip_id}
                  onClick={() => void onReevaluate(trip.trip_id)}
                >
                  <FormattedMessage id="myTrips.action.reevaluate" />
                </button>
                <button
                  type="button"
                  disabled={busyTripId === trip.trip_id}
                  onClick={() => void onShare(trip.trip_id)}
                >
                  <FormattedMessage id="myTrips.action.share" />
                </button>
                <button
                  type="button"
                  disabled={busyTripId === trip.trip_id}
                  onClick={() => void onDelete(trip.trip_id)}
                >
                  <FormattedMessage id="myTrips.action.delete" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {detail ? (
        <section className="my-trips-detail" aria-labelledby="my-trips-detail-heading">
          <h2 id="my-trips-detail-heading">
            <FormattedMessage id="myTrips.detail.title" />
          </h2>
          <p>
            <FormattedMessage id="tripPlanner.result.confidence" />: {detail.confidence}
          </p>
          {detail.last_change_summary ? (
            <section aria-labelledby="my-trips-changes-heading">
              <h3 id="my-trips-changes-heading">
                <FormattedMessage id="myTrips.detail.changes" />
              </h3>
              <pre className="my-trips-changes">
                {JSON.stringify(detail.last_change_summary, null, 2)}
              </pre>
            </section>
          ) : null}
          <ul className="trip-planner-components">
            {Object.entries(detail.components).map(([name, value]) => (
              <li key={name}>
                {name}: {typeof value === 'object' && value && 'status' in value
                  ? String((value as { status?: string }).status)
                  : JSON.stringify(value)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  )
}

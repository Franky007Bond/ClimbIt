import { useState, type FormEvent } from 'react'
import { FormattedMessage } from 'react-intl'
import { Link, useSearchParams } from 'react-router-dom'
import {
  createPlanRoutesRouteIdPlansPost,
  ensureTripCapabilityTripsCapabilityGet,
  saveTripTripsPost,
} from '../api/generated/sdk.gen'
import type { PlanResponse } from '../api/generated/types.gen'
import '../api/client'
import { recommendationClass } from '../features/trips/recommendationClass'

type SaveState = 'idle' | 'saving' | 'saved' | 'error'

export function TripPlannerPage() {
  const [searchParams] = useSearchParams()
  const [routeId, setRouteId] = useState(searchParams.get('routeId') ?? '')
  const [planDate, setPlanDate] = useState('2026-07-15')
  const [origin, setOrigin] = useState('Munich')
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [errorMessageId, setErrorMessageId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>('idle')

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setErrorMessageId(null)
    setSaveState('idle')
    setPlan(null)
    const result = await createPlanRoutesRouteIdPlansPost({
      path: { route_id: routeId.trim() },
      body: { plan_date: planDate, origin: origin.trim() },
      throwOnError: false,
    })
    setLoading(false)
    if (result.error || !result.response.ok || !result.data) {
      setErrorMessageId('tripPlanner.status.error')
      return
    }
    setPlan(result.data)
  }

  async function onSaveTrip() {
    if (!plan) {
      return
    }
    setSaveState('saving')
    await ensureTripCapabilityTripsCapabilityGet({ throwOnError: false })
    const result = await saveTripTripsPost({
      body: { plan_run_id: plan.plan_run_id },
      throwOnError: false,
    })
    if (!result.response.ok || !result.data) {
      setSaveState('error')
      return
    }
    setSaveState('saved')
  }

  return (
    <section className="trip-planner" aria-labelledby="trip-planner-heading">
      <header className="trip-planner-header">
        <h1 id="trip-planner-heading">
          <FormattedMessage id="page.tripPlanner.title" />
        </h1>
        <p className="trip-planner-lead">
          <FormattedMessage id="tripPlanner.lead" />
        </p>
      </header>

      <form className="trip-planner-form" onSubmit={(event) => void onSubmit(event)}>
        <label>
          <FormattedMessage id="tripPlanner.form.routeId" />
          <input
            name="routeId"
            value={routeId}
            onChange={(event) => setRouteId(event.target.value)}
            required
          />
        </label>
        <label>
          <FormattedMessage id="tripPlanner.form.planDate" />
          <input
            name="planDate"
            type="date"
            value={planDate}
            onChange={(event) => setPlanDate(event.target.value)}
            required
          />
        </label>
        <label>
          <FormattedMessage id="tripPlanner.form.origin" />
          <input
            name="origin"
            value={origin}
            onChange={(event) => setOrigin(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          <FormattedMessage id={loading ? 'tripPlanner.form.submitting' : 'tripPlanner.form.submit'} />
        </button>
      </form>

      {errorMessageId ? (
        <p className="trip-planner-error" role="alert">
          <FormattedMessage id={errorMessageId} />
        </p>
      ) : null}

      {plan ? (
        <div className="trip-planner-result">
          <div className="trip-planner-save">
            <button
              type="button"
              disabled={saveState === 'saving' || saveState === 'saved'}
              onClick={() => void onSaveTrip()}
            >
              <FormattedMessage
                id={
                  saveState === 'saving'
                    ? 'tripPlanner.save.saving'
                    : saveState === 'saved'
                      ? 'tripPlanner.save.saved'
                      : 'tripPlanner.save.action'
                }
              />
            </button>
            {saveState === 'saved' ? (
              <>
                <p className="trip-planner-save-success" role="status">
                  <FormattedMessage id="tripPlanner.save.success" />
                </p>
                <Link to="/trips" className="trip-planner-save-link">
                  <FormattedMessage id="tripPlanner.save.viewMyTrips" />
                </Link>
              </>
            ) : null}
            {saveState === 'error' ? (
              <p className="trip-planner-save-error" role="alert">
                <FormattedMessage id="tripPlanner.save.error" />
              </p>
            ) : null}
          </div>
          <div className={recommendationClass(plan.recommendation)} role="status">
            <FormattedMessage id="tripPlanner.result.recommendation" />:{' '}
            <span data-testid="recommendation-value">{plan.recommendation}</span>
          </div>
          <p>
            <FormattedMessage id="tripPlanner.result.confidence" />: {plan.confidence}
          </p>
          <section aria-labelledby="trip-planner-components-heading">
            <h2 id="trip-planner-components-heading">
              <FormattedMessage id="tripPlanner.components.title" />
            </h2>
            <ul className="trip-planner-components">
              {Object.entries(plan.components).map(([name, value]) => (
                <li key={name}>
                  <strong>{name}</strong>:{' '}
                  {typeof value === 'object' && value && 'status' in value
                    ? String((value as { status: string }).status)
                    : JSON.stringify(value)}
                </li>
              ))}
            </ul>
          </section>
          {plan.explanation.length > 0 ? (
            <section aria-labelledby="trip-planner-explanation-heading">
              <h2 id="trip-planner-explanation-heading">
                <FormattedMessage id="tripPlanner.explanation.title" />
              </h2>
              <ul>
                {plan.explanation.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>
          ) : null}
          <p className="trip-planner-disclaimer">
            {plan.safety_disclaimer}
          </p>
        </div>
      ) : null}
    </section>
  )
}

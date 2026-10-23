import { FormEvent, useState } from 'react'
import { FormattedMessage } from 'react-intl'
import { useSearchParams } from 'react-router-dom'
import { createPlanRoutesRouteIdPlansPost } from '../api/generated/sdk.gen'
import type { PlanResponse } from '../api/generated/types.gen'
import '../api/client'

function recommendationClass(recommendation: string): string {
  return `trip-planner-rec trip-planner-rec--${recommendation}`
}

export function TripPlannerPage() {
  const [searchParams] = useSearchParams()
  const [routeId, setRouteId] = useState(searchParams.get('routeId') ?? '')
  const [planDate, setPlanDate] = useState('2026-07-15')
  const [origin, setOrigin] = useState('Munich')
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [errorMessageId, setErrorMessageId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setErrorMessageId(null)
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

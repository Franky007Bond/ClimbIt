import { useEffect, useState } from 'react'
import { FormattedMessage } from 'react-intl'
import { useParams } from 'react-router-dom'
import { getSharedPlanSharesShareTokenGet } from '../api/generated/sdk.gen'
import type { SharedPlanSnapshot } from '../api/generated/types.gen'
import '../api/client'
import { recommendationClass } from '../features/trips/recommendationClass'

export function SharedPlanPage() {
  const { shareToken = '' } = useParams()
  const [plan, setPlan] = useState<SharedPlanSnapshot | null>(null)
  const [errorMessageId, setErrorMessageId] = useState<string | null>(null)

  useEffect(() => {
    if (!shareToken) {
      setErrorMessageId('sharedPlan.status.missingToken')
      return
    }
    void (async () => {
      const result = await getSharedPlanSharesShareTokenGet({
        path: { share_token: shareToken },
        throwOnError: false,
      })
      if (!result.response.ok || !result.data) {
        setPlan(null)
        setErrorMessageId('sharedPlan.status.notFound')
        return
      }
      setPlan(result.data)
      setErrorMessageId(null)
    })()
  }, [shareToken])

  return (
    <section className="shared-plan" aria-labelledby="shared-plan-heading">
      <header>
        <h1 id="shared-plan-heading">
          <FormattedMessage id="page.sharedPlan.title" />
        </h1>
        <p>
          <FormattedMessage id="sharedPlan.lead" />
        </p>
      </header>

      {errorMessageId ? (
        <p role="alert">
          <FormattedMessage id={errorMessageId} />
        </p>
      ) : null}

      {plan ? (
        <div className="shared-plan-body" data-testid="shared-plan-body">
          <p>
            <FormattedMessage id="tripPlanner.result.recommendation" />:{' '}
            <span className={recommendationClass(plan.recommendation)} role="status">
              {plan.recommendation}
            </span>
          </p>
          <p>
            <FormattedMessage id="tripPlanner.result.confidence" />: {plan.confidence}
          </p>
          {plan.origin_region ? (
            <p>
              <FormattedMessage
                id="sharedPlan.originRegion"
                values={{ region: plan.origin_region }}
              />
            </p>
          ) : null}
          <ul className="trip-planner-components">
            {Object.entries(plan.components).map(([name, value]) => (
              <li key={name}>
                {name}: {typeof value === 'object' && value && 'status' in value
                  ? String((value as { status?: string }).status)
                  : JSON.stringify(value)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

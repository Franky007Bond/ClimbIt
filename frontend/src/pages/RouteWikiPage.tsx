import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { FormattedMessage } from 'react-intl'
import {
  approveRevisionMaintainerRevisionsRevisionIdApprovePost,
  createMaintainerSessionMaintainerSessionsPost,
  getMaintainerSessionMaintainerSessionGet,
  getPendingRevisionsMaintainerRevisionsPendingGet,
  getRevisionDetailMaintainerRevisionsRevisionIdGet,
  rejectRevisionMaintainerRevisionsRevisionIdRejectPost,
} from '../api/generated/sdk.gen'
import type {
  FieldDiffItem,
  PendingRevisionItem,
  RevisionDetailResponse,
} from '../api/generated/types.gen'
import '../api/client'

type AuthState = 'loading' | 'anonymous' | 'authenticated'

function difficultyOriginal(snapshot: unknown): string | null {
  if (!snapshot || typeof snapshot !== 'object') {
    return null
  }
  const difficulty = (snapshot as { difficulty?: { original_value?: string } }).difficulty
  return difficulty?.original_value ?? null
}

function DiffPanel({ diffs }: { diffs: FieldDiffItem[] }) {
  const difficultyDiff = diffs.find((item) => item.field === 'difficulty')
  return (
    <section className="route-wiki-diff" aria-labelledby="route-wiki-diff-heading">
      <h2 id="route-wiki-diff-heading">
        <FormattedMessage id="routeWiki.diff.title" />
      </h2>
      <ul className="route-wiki-diff-list">
        {diffs.map((diff) => (
          <li key={diff.field}>
            <strong>
              <FormattedMessage id="routeWiki.diff.field" values={{ field: diff.field }} />
            </strong>
            {diff.field === 'difficulty' ? (
              <div className="route-wiki-difficulty-pair">
                <p>
                  <FormattedMessage id="routeWiki.diff.publishedGrade" />:{' '}
                  {difficultyOriginal(diff.before) ?? '—'}
                </p>
                <p>
                  <FormattedMessage id="routeWiki.diff.proposedGrade" />:{' '}
                  {difficultyOriginal(diff.after) ?? '—'}
                </p>
              </div>
            ) : (
              <p>
                <FormattedMessage id="routeWiki.diff.before" />: {JSON.stringify(diff.before)}
              </p>
            )}
          </li>
        ))}
      </ul>
      {difficultyDiff ? null : (
        <p className="route-wiki-diff-empty">
          <FormattedMessage id="routeWiki.diff.empty" />
        </p>
      )}
    </section>
  )
}

export function RouteWikiPage() {
  const [authState, setAuthState] = useState<AuthState>('loading')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState<PendingRevisionItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<RevisionDetailResponse | null>(null)
  const [statusMessageId, setStatusMessageId] = useState<string | null>(
    'routeWiki.status.loading',
  )

  const loadPending = useCallback(async () => {
    const result = await getPendingRevisionsMaintainerRevisionsPendingGet({
      throwOnError: false,
    })
    if (result.response.status === 401) {
      setAuthState('anonymous')
      setStatusMessageId('routeWiki.status.unauthorized')
      return
    }
    if (!result.response.ok || !result.data) {
      setStatusMessageId('routeWiki.status.error')
      return
    }
    setPending(result.data)
    setStatusMessageId(result.data.length === 0 ? 'routeWiki.queue.empty' : null)
  }, [])

  const loadSession = useCallback(async () => {
    const result = await getMaintainerSessionMaintainerSessionGet({ throwOnError: false })
    if (result.response.status === 401) {
      setAuthState('anonymous')
      setStatusMessageId('routeWiki.status.unauthorized')
      return
    }
    if (!result.response.ok || !result.data) {
      setAuthState('anonymous')
      setStatusMessageId('routeWiki.status.error')
      return
    }
    setAuthState('authenticated')
    setUsername(result.data.username)
    await loadPending()
  }, [loadPending])

  useEffect(() => {
    void loadSession()
  }, [loadSession])

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    void (async () => {
      const result = await getRevisionDetailMaintainerRevisionsRevisionIdGet({
        path: { revision_id: selectedId },
        throwOnError: false,
      })
      if (!result.response.ok || !result.data) {
        setStatusMessageId('routeWiki.status.error')
        return
      }
      setDetail(result.data)
    })()
  }, [selectedId])

  async function onLoginSubmit(event: FormEvent) {
    event.preventDefault()
    const result = await createMaintainerSessionMaintainerSessionsPost({
      body: { username, password },
      throwOnError: false,
    })
    setPassword('')
    if (result.response.status === 401) {
      setStatusMessageId('routeWiki.login.error')
      return
    }
    if (!result.response.ok) {
      setStatusMessageId('routeWiki.status.error')
      return
    }
    setAuthState('authenticated')
    await loadPending()
  }

  async function onApprove() {
    if (!selectedId) {
      return
    }
    const result = await approveRevisionMaintainerRevisionsRevisionIdApprovePost({
      path: { revision_id: selectedId },
      throwOnError: false,
    })
    if (result.response.status === 401) {
      setAuthState('anonymous')
      setStatusMessageId('routeWiki.status.unauthorized')
      return
    }
    if (result.response.status === 409 || result.response.status === 422) {
      setStatusMessageId('routeWiki.status.conflict')
      return
    }
    if (!result.response.ok) {
      setStatusMessageId('routeWiki.status.error')
      return
    }
    setSelectedId(null)
    await loadPending()
  }

  async function onReject() {
    if (!selectedId) {
      return
    }
    const result = await rejectRevisionMaintainerRevisionsRevisionIdRejectPost({
      path: { revision_id: selectedId },
      throwOnError: false,
    })
    if (result.response.status === 401) {
      setAuthState('anonymous')
      setStatusMessageId('routeWiki.status.unauthorized')
      return
    }
    if (!result.response.ok) {
      setStatusMessageId('routeWiki.status.error')
      return
    }
    setSelectedId(null)
    await loadPending()
  }

  return (
    <main className="route-wiki-page">
      <header className="route-wiki-header">
        <h1>
          <FormattedMessage id="routeWiki.queue.title" />
        </h1>
        <p>
          <FormattedMessage id="routeWiki.queue.subtitle" />
        </p>
      </header>

      {authState === 'loading' ? (
        <p role="status">
          <FormattedMessage id="routeWiki.status.loading" />
        </p>
      ) : null}

      {authState === 'anonymous' ? (
        <section className="route-wiki-login" aria-labelledby="route-wiki-login-heading">
          <h2 id="route-wiki-login-heading">
            <FormattedMessage id="routeWiki.login.title" />
          </h2>
          <p>
            <FormattedMessage id="routeWiki.login.required" />
          </p>
          <form onSubmit={onLoginSubmit}>
            <label>
              <FormattedMessage id="routeWiki.login.username" />
              <input
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
            <label>
              <FormattedMessage id="routeWiki.login.password" />
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button type="submit">
              <FormattedMessage id="routeWiki.login.submit" />
            </button>
          </form>
        </section>
      ) : null}

      {statusMessageId ? (
        <p role="status" className="route-wiki-status">
          <FormattedMessage id={statusMessageId as never} />
        </p>
      ) : null}

      {authState === 'authenticated' ? (
        <div className="route-wiki-layout">
          <section className="route-wiki-queue" aria-labelledby="route-wiki-queue-heading">
            <h2 id="route-wiki-queue-heading">
              <FormattedMessage id="routeWiki.queue.listTitle" />
            </h2>
            <ul>
              {pending.map((item) => (
                <li key={item.revision_id}>
                  <button
                    type="button"
                    className={
                      selectedId === item.revision_id ? 'route-wiki-queue-selected' : undefined
                    }
                    onClick={() => setSelectedId(item.revision_id)}
                  >
                    {item.route_name} (#{item.revision_number})
                  </button>
                </li>
              ))}
            </ul>
          </section>
          {detail ? (
            <section className="route-wiki-detail">
              <DiffPanel diffs={detail.field_diffs} />
              <div className="route-wiki-actions">
                <button type="button" onClick={() => void onApprove()}>
                  <FormattedMessage id="routeWiki.action.approve" />
                </button>
                <button type="button" onClick={() => void onReject()}>
                  <FormattedMessage id="routeWiki.action.reject" />
                </button>
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </main>
  )
}

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter } from 'react-router-dom'
import {
  getMaintainerSessionMaintainerSessionGet,
  getPendingRevisionsMaintainerRevisionsPendingGet,
  getRevisionDetailMaintainerRevisionsRevisionIdGet,
} from '../api/generated/sdk.gen'
import { en, messagesByLocale, defaultLocale } from '../i18n/messages'
import { RouteWikiPage } from './RouteWikiPage'

vi.mock('../api/generated/sdk.gen', () => ({
  approveRevisionMaintainerRevisionsRevisionIdApprovePost: vi.fn(),
  createMaintainerSessionMaintainerSessionsPost: vi.fn(),
  deleteMaintainerSessionMaintainerSessionsDelete: vi.fn(),
  getMaintainerSessionMaintainerSessionGet: vi.fn(),
  getPendingRevisionsMaintainerRevisionsPendingGet: vi.fn(),
  getRevisionDetailMaintainerRevisionsRevisionIdGet: vi.fn(),
  rejectRevisionMaintainerRevisionsRevisionIdRejectPost: vi.fn(),
}))

const revisionId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'

function renderPage() {
  return render(
    <IntlProvider locale={defaultLocale} messages={messagesByLocale[defaultLocale]}>
      <MemoryRouter>
        <RouteWikiPage />
      </MemoryRouter>
    </IntlProvider>,
  )
}

describe('RouteWikiPage', () => {
  beforeEach(() => {
    vi.mocked(getMaintainerSessionMaintainerSessionGet).mockResolvedValue({
      data: { username: 'operator' },
      response: new Response(null, { status: 200 }),
      error: undefined,
    } as never)
    vi.mocked(getPendingRevisionsMaintainerRevisionsPendingGet).mockResolvedValue({
      data: [
        {
          revision_id: revisionId,
          route_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
          route_name: 'Test Route',
          revision_number: 2,
          created_at: '2026-10-23T08:00:00+00:00',
          author_kind: 'anonymous',
          changed_keys: ['difficulty'],
        },
      ],
      response: new Response(null, { status: 200 }),
      error: undefined,
    } as never)
    vi.mocked(getRevisionDetailMaintainerRevisionsRevisionIdGet).mockResolvedValue({
      data: {
        revision_id: revisionId,
        route_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        application_status: 'pending',
        revision_number: 2,
        created_at: '2026-10-23T08:00:00+00:00',
        author_kind: 'anonymous',
        field_diffs: [
          {
            field: 'difficulty',
            before: { difficulty: { original_value: 'K3', original_scale: 'k1_k6' } },
            after: { difficulty: { original_value: 'K4', original_scale: 'k1_k6' } },
          },
        ],
      },
      response: new Response(null, { status: 200 }),
      error: undefined,
    } as never)
  })

  it('shows published and proposed difficulty labels from the catalog', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText(en['routeWiki.queue.listTitle'])).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Test Route/i }))

    await waitFor(() => {
      expect(screen.getByText(new RegExp(en['routeWiki.diff.publishedGrade']))).toBeInTheDocument()
      expect(screen.getByText(new RegExp(en['routeWiki.diff.proposedGrade']))).toBeInTheDocument()
      expect(document.body.textContent).toContain('K3')
      expect(document.body.textContent).toContain('K4')
    })
  })
})

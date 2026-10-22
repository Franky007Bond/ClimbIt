import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter } from 'react-router-dom'
import { listRoutesRoutesGet } from '../../api/generated/sdk.gen'
import type { RouteSearchItem } from '../../api/generated/types.gen'
import { en, messagesByLocale, defaultLocale } from '../../i18n/messages'
import { ExploreRoutesPage } from '../../pages/ExploreRoutesPage'

vi.mock('../../api/generated/sdk.gen', () => ({
  listRoutesRoutesGet: vi.fn(),
}))

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="explore-map">{children}</div>
  ),
  TileLayer: () => null,
  CircleMarker: () => null,
  useMap: () => ({
    setView: vi.fn(),
    fitBounds: vi.fn(),
  }),
}))

function mockRoute(
  overrides: Partial<RouteSearchItem> & Pick<RouteSearchItem, 'id' | 'name'>,
): RouteSearchItem {
  return {
    route_type: 'alpine_hike',
    trailhead: { longitude: 10.5, latitude: 47.2 },
    region: { name: 'Allgäu', country: 'DE', coverage: 'sample' },
    publication: 'published',
    provenance: 'seed',
    completeness: 'complete',
    assessment: 'unassessed',
    duration_minutes: 180,
    duration_is_estimated: false,
    transit_accessibility: 'unknown',
    season_months: [6, 7, 8],
    difficulty: null,
    ...overrides,
  }
}

function okRoutesResponse(routes: RouteSearchItem[]) {
  return {
    data: { routes },
    error: undefined,
    response: { ok: true } as Response,
    request: new Request('http://127.0.0.1:8000/routes'),
  }
}

function renderExplorePage() {
  return render(
    <IntlProvider locale={defaultLocale} messages={messagesByLocale[defaultLocale]}>
      <MemoryRouter initialEntries={['/']}>
        <ExploreRoutesPage />
      </MemoryRouter>
    </IntlProvider>,
  )
}

describe('ExploreRoutesPage filters', () => {
  const initialRoutes = [
    mockRoute({ id: '11111111-1111-4111-8111-111111111111', name: 'Alpine Alpha' }),
    mockRoute({
      id: '22222222-2222-4222-8222-222222222222',
      name: 'Alpine Beta',
      route_type: 'klettersteig',
    }),
  ]

  const filteredRoutes = [
    mockRoute({
      id: '33333333-3333-4333-8333-333333333333',
      name: 'Steig Summit',
      route_type: 'klettersteig',
    }),
  ]

  beforeEach(() => {
    vi.mocked(listRoutesRoutesGet).mockImplementation(async (options) => {
      const type = options?.query?.route_type
      const month = options?.query?.season_month
      if (type === 'klettersteig' && month === 7) {
        return okRoutesResponse(filteredRoutes)
      }
      if (type === 'klettersteig') {
        return okRoutesResponse(filteredRoutes)
      }
      return okRoutesResponse(initialRoutes)
    })
  })

  it('loads the initial list and refetches when route type and season change', async () => {
    renderExplorePage()

    expect(await screen.findByText('Alpine Alpha')).toBeInTheDocument()
    expect(screen.getByText('Alpine Beta')).toBeInTheDocument()

    const routeTypeSelect = screen.getByRole('combobox', {
      name: en['explore.filter.routeType.label'],
    })
    fireEvent.change(routeTypeSelect, { target: { value: 'klettersteig' } })

    await waitFor(() => {
      expect(screen.getByText('Steig Summit')).toBeInTheDocument()
    })
    expect(screen.queryByText('Alpine Alpha')).not.toBeInTheDocument()

    const seasonSelect = screen.getByRole('combobox', {
      name: en['explore.filter.season.label'],
    })
    fireEvent.change(seasonSelect, { target: { value: '7' } })

    await waitFor(() => {
      expect(listRoutesRoutesGet).toHaveBeenLastCalledWith(
        expect.objectContaining({
          query: expect.objectContaining({
            route_type: 'klettersteig',
            season_month: 7,
          }),
        }),
      )
    })
  })
})

describe('ExploreRoutesPage load failures', () => {
  beforeEach(() => {
    vi.mocked(listRoutesRoutesGet).mockResolvedValue({
      data: undefined,
      error: {},
      response: { ok: false, status: 503 } as Response,
      request: new Request('http://127.0.0.1:8000/routes'),
    })
  })

  it('shows a catalog error message instead of an empty list', async () => {
    renderExplorePage()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      en['explore.status.error'],
    )
  })
})

import { render, screen } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { getRouteDetailRoutesRouteIdGet } from '../api/generated/sdk.gen'
import type { RouteDetail } from '../api/generated/types.gen'
import { en, messagesByLocale, defaultLocale } from '../i18n/messages'
import { RouteDetailPage } from './RouteDetailPage'

vi.mock('../api/generated/sdk.gen', () => ({
  getRouteDetailRoutesRouteIdGet: vi.fn(),
}))

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="route-detail-map">{children}</div>
  ),
  TileLayer: () => null,
  CircleMarker: () => null,
  Polyline: () => null,
  useMap: () => ({
    setView: vi.fn(),
    fitBounds: vi.fn(),
  }),
}))

const routeId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'

function mockRouteDetail(overrides: Partial<RouteDetail> = {}): RouteDetail {
  return {
    id: routeId,
    name: 'Test Klettersteig',
    route_type: 'klettersteig',
    description: 'A sample route for testing.',
    publication: 'published',
    provenance: 'seed',
    completeness: 'complete',
    assessment: 'unassessed',
    region: { name: 'Allgäu', country: 'DE', coverage: 'sample' },
    trailhead: { latitude: 47.4, longitude: 10.2 },
    linestring: {
      points: [
        { latitude: 47.4, longitude: 10.2 },
        { latitude: 47.41, longitude: 10.21 },
      ],
    },
    difficulty: {
      mapped_huebler: 'C',
      original_value: 'K3',
      original_scale: 'k1_k6',
      mapping_citation: 'seed',
      mapping_confidence: 'exact',
      mapping_source: 'table',
      mapping_version: '1',
      route_type: 'klettersteig',
      structured_scale: 'k1_k6',
      structured_value: 'K3',
    },
    approach_minutes: null,
    closure_assessment: null,
    descent_minutes: null,
    duration_is_estimated: false,
    duration_minutes: 240,
    elevation_gain_m: null,
    elevation_loss_m: null,
    elevation_max_m: null,
    elevation_min_m: null,
    gpx: null,
    official_source_links: [],
    season_months: [6, 7, 8],
    season_note: null,
    technical_minutes: null,
    transit_accessibility: 'unknown',
    ...overrides,
  }
}

function okDetailResponse(route: RouteDetail) {
  return {
    data: route,
    error: undefined,
    response: { ok: true, status: 200 } as Response,
    request: new Request(`http://127.0.0.1:8000/routes/${route.id}`),
  }
}

function renderRouteDetail(initialEntry = `/routes/${routeId}`) {
  return render(
    <IntlProvider locale={defaultLocale} messages={messagesByLocale[defaultLocale]}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="routes/:routeId" element={<RouteDetailPage />} />
        </Routes>
      </MemoryRouter>
    </IntlProvider>,
  )
}

describe('RouteDetailPage', () => {
  beforeEach(() => {
    vi.mocked(getRouteDetailRoutesRouteIdGet).mockResolvedValue(
      okDetailResponse(mockRouteDetail()),
    )
  })

  it('shows original K3 and normalized grade when difficulty is mapped', async () => {
    renderRouteDetail()

    expect(await screen.findByRole('heading', { name: 'Test Klettersteig' })).toBeInTheDocument()
    expect(screen.getByText('K3')).toBeInTheDocument()
    expect(screen.getByText('C')).toBeInTheDocument()
    expect(getRouteDetailRoutesRouteIdGet).toHaveBeenCalledWith(
      expect.objectContaining({
        path: { route_id: routeId },
      }),
    )
  })

  it('shows a distinct not-found message for HTTP 404', async () => {
    vi.mocked(getRouteDetailRoutesRouteIdGet).mockResolvedValue({
      data: undefined,
      error: {},
      response: { ok: false, status: 404 } as Response,
      request: new Request(`http://127.0.0.1:8000/routes/${routeId}`),
    })

    renderRouteDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      en['routeDetail.status.notFound'],
    )
    expect(screen.queryByRole('heading', { name: 'Test Klettersteig' })).not.toBeInTheDocument()
  })

  it('shows not-found for HTTP 422 invalid route id', async () => {
    vi.mocked(getRouteDetailRoutesRouteIdGet).mockResolvedValue({
      data: undefined,
      error: { detail: [] },
      response: { ok: false, status: 422 } as Response,
      request: new Request('http://127.0.0.1:8000/routes/not-a-uuid'),
    })

    renderRouteDetail('/routes/not-a-uuid')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      en['routeDetail.status.notFound'],
    )
    expect(screen.queryByText(en['routeDetail.status.error'])).not.toBeInTheDocument()
  })
})

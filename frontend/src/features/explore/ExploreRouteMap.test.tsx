import { fireEvent, render, screen } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter } from 'react-router-dom'
import type { RouteSearchItem } from '../../api/generated/types.gen'
import { defaultLocale, messagesByLocale } from '../../i18n/messages'
import { ExploreRouteMap } from './ExploreRouteMap'

const navigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  )
  return {
    ...actual,
    useNavigate: () => navigate,
  }
})

vi.mock('../map/ClimbItMapContainer', () => ({
  ClimbItMapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="explore-map">{children}</div>
  ),
}))

vi.mock('react-leaflet', () => ({
  CircleMarker: ({
    eventHandlers,
    children,
    interactive,
  }: {
    eventHandlers?: { click?: () => void }
    children?: React.ReactNode
    interactive?: boolean
  }) =>
    interactive === false ? null : (
      <button type="button" data-testid="route-marker" onClick={eventHandlers?.click}>
        {children}
      </button>
    ),
  Tooltip: ({ children }: { children: React.ReactNode }) => (
    <span>{children}</span>
  ),
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

describe('ExploreRouteMap', () => {
  beforeEach(() => {
    navigate.mockReset()
  })

  it('navigates to the route detail when a map marker is clicked', () => {
    const route = mockRoute({
      id: '11111111-1111-4111-8111-111111111111',
      name: 'Alpine Alpha',
    })

    render(
      <IntlProvider locale={defaultLocale} messages={messagesByLocale[defaultLocale]}>
        <MemoryRouter>
          <ExploreRouteMap routes={[route]} />
        </MemoryRouter>
      </IntlProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Alpine Alpha' }))

    expect(navigate).toHaveBeenCalledWith(
      '/routes/11111111-1111-4111-8111-111111111111',
    )
  })
})

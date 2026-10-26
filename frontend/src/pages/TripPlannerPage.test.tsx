import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import en from '../i18n/en.json'
import { TripPlannerPage } from './TripPlannerPage'
import {
  createPlanRoutesRouteIdPlansPost,
  ensureTripCapabilityTripsCapabilityGet,
  saveTripTripsPost,
} from '../api/generated/sdk.gen'

vi.mock('../api/generated/sdk.gen', () => ({
  createPlanRoutesRouteIdPlansPost: vi.fn(),
  ensureTripCapabilityTripsCapabilityGet: vi.fn(),
  saveTripTripsPost: vi.fn(),
}))

function renderPage() {
  return render(
    <IntlProvider locale="en" messages={en}>
      <MemoryRouter>
        <TripPlannerPage />
      </MemoryRouter>
    </IntlProvider>,
  )
}

describe('TripPlannerPage', () => {
  it('shows unknown recommendation without green styling when closure is missing', async () => {
    vi.mocked(createPlanRoutesRouteIdPlansPost).mockResolvedValue({
      data: {
        plan_run_id: 'run-1',
        route_id: 'route-1',
        plan_date: '2026-07-15',
        trailhead_timezone: 'Europe/Paris',
        safety_disclaimer: 'Disclaimer text.',
        recommendation: 'unknown',
        confidence: 'low',
        trace_id: null,
        avalanche: null,
        components: {
          closure: { status: 'unknown', planning_value: 'unknown' },
          weather: { status: 'ok', freshness: 'ok' },
        },
        weather: null,
        gear: [],
        daylight: { latest_safe_start_local: null, be_off_by_local: null, explanation: [] },
        explanation: ['Closure assessment is missing, unreviewed, or expired.'],
        thunderstorm: { risk: 'low', factors: [], label: 'heuristic', heuristic_version: 'v1' },
        transit_summary: 'Mock',
        origin_region: 'DE-BY',
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
      request: new Request('http://127.0.0.1:8000/routes/x/plans'),
    })

    renderPage()
    fireEvent.change(screen.getByLabelText(en['tripPlanner.form.routeId']), {
      target: { value: '50620691-2211-5a6e-8dfd-1c5bf7af289b' },
    })
    fireEvent.click(screen.getByRole('button', { name: en['tripPlanner.form.submit'] }))

    await waitFor(() => {
      expect(screen.getByTestId('recommendation-value')).toHaveTextContent('unknown')
    })
    const badge = screen.getByRole('status')
    expect(badge.className).toContain('trip-planner-rec--unknown')
    expect(badge.className).not.toContain('trip-planner-rec--green')
  })

  it('saves the plan run to My Trips', async () => {
    vi.mocked(createPlanRoutesRouteIdPlansPost).mockResolvedValue({
      data: {
        plan_run_id: 'run-42',
        route_id: 'route-1',
        plan_date: '2026-07-15',
        trailhead_timezone: 'Europe/Paris',
        safety_disclaimer: 'Disclaimer text.',
        recommendation: 'go',
        confidence: 'high',
        trace_id: null,
        avalanche: null,
        components: {},
        weather: null,
        gear: [],
        daylight: { latest_safe_start_local: null, be_off_by_local: null, explanation: [] },
        explanation: [],
        thunderstorm: { risk: 'low', factors: [], label: 'heuristic', heuristic_version: 'v1' },
        transit_summary: 'Mock',
        origin_region: 'DE-BY',
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
      request: new Request('http://127.0.0.1:8000/routes/x/plans'),
    })
    vi.mocked(ensureTripCapabilityTripsCapabilityGet).mockResolvedValue({
      data: { status: 'ready' },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
      request: new Request('http://127.0.0.1:8000/trips/capability'),
    })
    vi.mocked(saveTripTripsPost).mockResolvedValue({
      data: {
        trip_id: 'trip-1',
        route_id: 'route-1',
        latest_plan_run_id: 'run-42',
        plan_date: '2026-07-15',
        recommendation: 'go',
        last_change_summary: null,
      },
      error: undefined,
      response: { ok: true, status: 201 } as Response,
      request: new Request('http://127.0.0.1:8000/trips'),
    })

    renderPage()
    fireEvent.change(screen.getByLabelText(en['tripPlanner.form.routeId']), {
      target: { value: '50620691-2211-5a6e-8dfd-1c5bf7af289b' },
    })
    fireEvent.click(screen.getByRole('button', { name: en['tripPlanner.form.submit'] }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: en['tripPlanner.save.action'] })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: en['tripPlanner.save.action'] }))

    await waitFor(() => {
      expect(saveTripTripsPost).toHaveBeenCalledWith({
        body: { plan_run_id: 'run-42' },
        throwOnError: false,
      })
    })
    expect(screen.getByText(en['tripPlanner.save.success'])).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: en['tripPlanner.save.viewMyTrips'] }),
    ).toHaveAttribute('href', '/trips')
  })
})

import { render, screen, waitFor } from '@testing-library/react'
import { IntlProvider } from 'react-intl'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import en from '../i18n/en.json'
import { SharedPlanPage } from './SharedPlanPage'
import { getSharedPlanSharesShareTokenGet } from '../api/generated/sdk.gen'

vi.mock('../api/generated/sdk.gen', () => ({
  getSharedPlanSharesShareTokenGet: vi.fn(),
}))

function renderPage(token: string) {
  return render(
    <IntlProvider locale="en" messages={en}>
      <MemoryRouter initialEntries={[`/share/${token}`]}>
        <Routes>
          <Route path="/share/:shareToken" element={<SharedPlanPage />} />
        </Routes>
      </MemoryRouter>
    </IntlProvider>,
  )
}

describe('SharedPlanPage', () => {
  it('renders a shared plan without origin or capability fields', async () => {
    vi.mocked(getSharedPlanSharesShareTokenGet).mockResolvedValue({
      data: {
        plan_run_id: 'run-1',
        route_id: 'route-1',
        plan_date: '2026-07-15',
        recommendation: 'yellow',
        confidence: 'medium',
        components: {
          weather: { status: 'ok', freshness: 'ok' },
        },
        explanation: ['Sample explanation.'],
        origin_region: 'DE-BY',
      },
      error: undefined,
      response: { ok: true, status: 200 } as Response,
      request: new Request('http://127.0.0.1:8000/shares/token'),
    })

    renderPage('token-abc')
    await waitFor(() => {
      expect(screen.getByTestId('shared-plan-body')).toBeInTheDocument()
    })

    const text = screen.getByTestId('shared-plan-body').textContent ?? ''
    expect(text.toLowerCase()).not.toContain('origin (')
    expect(text.toLowerCase()).not.toContain('capability')
    expect(text).toContain('DE-BY')
    expect(text).toContain('yellow')
  })
})

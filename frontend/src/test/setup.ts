import '@testing-library/jest-dom/vitest'

vi.mock('../api/generated/sdk.gen', () => ({
  listRoutesRoutesGet: vi.fn(() =>
    Promise.resolve({
      data: { routes: [] },
      error: undefined,
      response: { ok: true } as Response,
      request: new Request('http://127.0.0.1:8000/routes'),
    }),
  ),
  getRouteDetailRoutesRouteIdGet: vi.fn(),
  healthHealthGet: vi.fn(),
  readyReadyGet: vi.fn(),
}))

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverStub)

import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import type { AppRouteHandle } from './components/appNav'
import { ExploreRoutesPage } from './pages/ExploreRoutesPage'
import { MyTripsPage } from './pages/MyTripsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { RouteDetailPage } from './pages/RouteDetailPage'
import { RouteWikiPage } from './pages/RouteWikiPage'
import { SharedPlanPage } from './pages/SharedPlanPage'
import { TripPlannerPage } from './pages/TripPlannerPage'

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          index
          element={<ExploreRoutesPage />}
          handle={{ navSection: 'explore' } satisfies AppRouteHandle}
        />
        <Route
          path="routes/:routeId"
          element={<RouteDetailPage />}
          handle={{ navSection: 'routeDetail' } satisfies AppRouteHandle}
        />
        <Route
          path="plan"
          element={<TripPlannerPage />}
          handle={{ navSection: 'tripPlanner' } satisfies AppRouteHandle}
        />
        <Route
          path="trips"
          element={<MyTripsPage />}
          handle={{ navSection: 'myTrips' } satisfies AppRouteHandle}
        />
        <Route
          path="share/:shareToken"
          element={<SharedPlanPage />}
          handle={{ navSection: 'tripPlanner' } satisfies AppRouteHandle}
        />
        <Route
          path="review"
          element={<RouteWikiPage />}
          handle={{ navSection: 'routeWiki' } satisfies AppRouteHandle}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App

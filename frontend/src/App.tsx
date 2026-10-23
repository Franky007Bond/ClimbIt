import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
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
        <Route index element={<ExploreRoutesPage />} />
        <Route path="routes/:routeId" element={<RouteDetailPage />} />
        <Route path="plan" element={<TripPlannerPage />} />
        <Route path="trips" element={<MyTripsPage />} />
        <Route path="share/:shareToken" element={<SharedPlanPage />} />
        <Route path="review" element={<RouteWikiPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App

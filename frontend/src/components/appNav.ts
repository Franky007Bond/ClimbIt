import { matchPath } from 'react-router-dom'

export type AppNavSection =
  | 'explore'
  | 'routeDetail'
  | 'tripPlanner'
  | 'myTrips'
  | 'routeWiki'

export type AppRouteHandle = {
  navSection: AppNavSection
}

export function navLinkClassName(isActive: boolean): string {
  return isActive ? 'nav-link nav-link-active' : 'nav-link'
}

export function navSectionForPathname(pathname: string): AppNavSection | undefined {
  if (matchPath({ path: '/', end: true }, pathname)) {
    return 'explore'
  }
  if (matchPath({ path: '/routes/:routeId', end: true }, pathname)) {
    return 'routeDetail'
  }
  if (
    matchPath({ path: '/plan', end: true }, pathname) ||
    matchPath({ path: '/share/:shareToken', end: true }, pathname)
  ) {
    return 'tripPlanner'
  }
  if (matchPath({ path: '/trips', end: true }, pathname)) {
    return 'myTrips'
  }
  if (matchPath({ path: '/review', end: true }, pathname)) {
    return 'routeWiki'
  }
  return undefined
}

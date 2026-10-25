import { useLocation } from 'react-router-dom'
import type { AppNavSection } from './appNav'
import { navSectionForPathname } from './appNav'

export function useAppNavSection(): AppNavSection | undefined {
  const { pathname } = useLocation()
  return navSectionForPathname(pathname)
}

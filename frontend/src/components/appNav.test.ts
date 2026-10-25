import { navSectionForPathname } from './appNav'

describe('navSectionForPathname', () => {
  it('maps primary app paths to nav sections', () => {
    expect(navSectionForPathname('/')).toBe('explore')
    expect(navSectionForPathname('/routes/11111111-1111-4111-8111-111111111111')).toBe(
      'routeDetail',
    )
    expect(navSectionForPathname('/plan')).toBe('tripPlanner')
    expect(navSectionForPathname('/share/abc')).toBe('tripPlanner')
    expect(navSectionForPathname('/trips')).toBe('myTrips')
    expect(navSectionForPathname('/review')).toBe('routeWiki')
  })
})

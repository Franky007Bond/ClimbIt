import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MapAttribution } from './MapAttribution'

describe('MapAttribution', () => {
  it('shows OpenStreetMap attribution text', () => {
    render(<MapAttribution />)
    const node = screen.getByTestId('map-attribution')
    expect(node.textContent).toContain('OpenStreetMap')
  })
})

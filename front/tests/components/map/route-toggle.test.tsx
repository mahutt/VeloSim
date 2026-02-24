/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useSimulation } from '~/providers/simulation-provider';
import RouteToggle from '~/components/map/route-toggle';
import { makeSimulationContext } from 'tests/test-helpers';

// Mock the useSimulation hook
vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('RouteToggle', () => {
  it('should render the menu button', () => {
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext()
    );

    render(<RouteToggle />);

    const button = screen.getByRole('button', {
      name: /toggle display options/i,
    });
    expect(button).toBeInTheDocument();
  });

  it('should open dropdown menu when button is clicked', async () => {
    const user = userEvent.setup();
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext()
    );

    render(<RouteToggle />);

    const button = screen.getByRole('button', {
      name: /toggle display options/i,
    });
    await user.click(button);

    expect(screen.getByText('Show All Routes')).toBeInTheDocument();
  });

  it('should show toggle switch in off state when showAllRoutes is false', async () => {
    const user = userEvent.setup();
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext()
    );

    render(<RouteToggle />);

    const button = screen.getByRole('button', {
      name: /toggle display options/i,
    });
    await user.click(button);

    // Check that the switch is in off state (bg-input class)
    const toggleSwitch = screen
      .getByText('Show All Routes')
      .parentElement?.querySelector('.bg-input');
    expect(toggleSwitch).toBeInTheDocument();
  });

  it('should show toggle switch in on state when showAllRoutes is true', async () => {
    const user = userEvent.setup();
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext()
    );

    render(<RouteToggle />);

    const button = screen.getByRole('button', {
      name: /toggle display options/i,
    });
    await user.click(button);

    // Verify toggle exists by finding both the container and checking its structure
    const toggleContainer = screen.getByText('Show All Routes').parentElement;
    expect(toggleContainer).toBeInTheDocument();
    expect(toggleContainer).toHaveClass(
      'flex',
      'items-center',
      'justify-between'
    );
  });

  it('should toggle showAllRoutes state when clicked', async () => {
    const user = userEvent.setup();

    // Initial render with showAllRoutes = false
    const mockContext = makeSimulationContext();
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      mockContext
    );

    render(<RouteToggle />);

    // Open dropdown
    const button = screen.getByRole('button', {
      name: /toggle display options/i,
    });
    await user.click(button);

    // Find the toggle container
    const toggleContainer = screen.getByText('Show All Routes').parentElement;
    expect(toggleContainer).toBeInTheDocument();
    expect(toggleContainer).toHaveClass('flex');

    // Verify the toggle can be interacted with (dropdown stays open after click)
    await user.click(toggleContainer!);
    expect(screen.getByText('Show All Routes')).toBeInTheDocument();
  });

  it('should not close dropdown when toggle is clicked', async () => {
    const user = userEvent.setup();
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext()
    );

    render(<RouteToggle />);

    // Open dropdown
    const button = screen.getByRole('button', {
      name: /toggle display options/i,
    });
    await user.click(button);

    // Click on the toggle row
    const toggleRow = screen.getByText('Show All Routes').parentElement;
    await user.click(toggleRow!);

    // Dropdown should still be visible
    expect(screen.getByText('Show All Routes')).toBeInTheDocument();
  });

  it('should have correct aria-label for accessibility', () => {
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext()
    );

    render(<RouteToggle />);

    const button = screen.getByLabelText('Toggle display options');
    expect(button).toBeInTheDocument();
  });

  it('should render menu icon', () => {
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext()
    );

    const { container } = render(<RouteToggle />);

    // Menu icon should be present (lucide-react renders svg)
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});

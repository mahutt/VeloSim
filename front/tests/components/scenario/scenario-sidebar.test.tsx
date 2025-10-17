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
import { render, screen, fireEvent } from '@testing-library/react';
import ScenarioSidebar from '../../../app/components/scenario/scenario-sidebar';
import type { Scenario } from '~/types';

// Mock getScenarioPreview
vi.mock('~/lib/scenario-utils', () => ({
  getScenarioPreview: (scenario: Scenario) => `Preview for ${scenario.name}`,
}));

// Mock Card and CardContent to simple divs for easier testing
import React from 'react';
vi.mock('~/components/ui/card', () => ({
  Card: (props: React.HTMLAttributes<HTMLDivElement>) => <div {...props} />,
  CardContent: (props: React.HTMLAttributes<HTMLDivElement>) => (
    <div {...props} />
  ),
}));

const scenarios: Scenario[] = [
  { id: 1, name: 'Scenario 1' } as Scenario,
  { id: 2, name: 'Scenario 2' } as Scenario,
];

describe('ScenarioSidebar', () => {
  it('renders the sidebar title', () => {
    render(
      <ScenarioSidebar
        scenarios={scenarios}
        selectedScenarioId={null}
        onSelect={() => {}}
      />
    );
    expect(screen.getByText('Saved Scenarios')).toBeInTheDocument();
  });

  it('shows "No saved scenarios" when scenarios is empty', () => {
    render(
      <ScenarioSidebar
        scenarios={[]}
        selectedScenarioId={null}
        onSelect={() => {}}
      />
    );
    expect(screen.getByText('No saved scenarios')).toBeInTheDocument();
  });

  it('renders all scenario cards', () => {
    render(
      <ScenarioSidebar
        scenarios={scenarios}
        selectedScenarioId={null}
        onSelect={() => {}}
      />
    );
    expect(screen.getByText('Scenario 1')).toBeInTheDocument();
    expect(screen.getByText('Scenario 2')).toBeInTheDocument();
    expect(screen.getByText('Preview for Scenario 1')).toBeInTheDocument();
    expect(screen.getByText('Preview for Scenario 2')).toBeInTheDocument();
  });

  it('highlights the selected scenario', () => {
    render(
      <ScenarioSidebar
        scenarios={scenarios}
        selectedScenarioId={2}
        onSelect={() => {}}
      />
    );
    const selectedCard =
      screen.getByText('Scenario 2').parentElement?.parentElement;
    expect(selectedCard?.className).toContain(
      'flex items-start justify-between gap-2'
    );
  });

  it('calls onSelect when a scenario is clicked', () => {
    const onSelect = vi.fn();
    render(
      <ScenarioSidebar
        scenarios={scenarios}
        selectedScenarioId={null}
        onSelect={onSelect}
      />
    );
    fireEvent.click(screen.getByText('Scenario 1'));
    expect(onSelect).toHaveBeenCalledWith(scenarios[0]);
  });
});

import { expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import Simulation, { meta } from '~/routes/simulation';
import { createRoutesStub } from 'react-router';

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
});

test('simulation page loads the map container', async () => {
  const Stub = createRoutesStub([
    {
      path: '/simulation',
      Component: Simulation,
    },
  ]);

  render(<Stub initialEntries={['/simulation']} />);
  expect(screen.getByTestId('map-container')).toBeInTheDocument();
});

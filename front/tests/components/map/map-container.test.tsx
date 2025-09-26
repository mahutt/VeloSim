import { expect, test } from 'vitest';
import { render } from '@testing-library/react';
import MapContainer from '~/components/map/map-container';

test('map container render should fail without a map provider', async () => {
  expect(() => {
    render(<MapContainer />);
  }).toThrow('useMap must be used within a MapProvider');
});

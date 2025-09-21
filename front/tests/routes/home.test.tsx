import { expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import Home, { meta } from '~/routes/home';

test('home pages loads 1 button', async () => {
  render(<Home />);

  expect(screen.getAllByRole('button')).toHaveLength(1);
});

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
  expect(metaInfo[1].name).toBeDefined();
  expect(metaInfo[1].content).toBeDefined();
});

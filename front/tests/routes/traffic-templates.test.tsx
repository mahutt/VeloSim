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

import { beforeEach, expect, test, vi } from 'vitest';
import { createRoutesStub } from 'react-router';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import api from '~/api';
import TrafficTemplates, { meta } from '~/routes/traffic-templates';

vi.mock('~/api');
vi.mock('~/hooks/use-auth', () => ({
  default: () => ({
    user: {
      id: 1,
      username: 'admin',
      is_admin: true,
      is_enabled: true,
    },
    loading: false,
  }),
}));

beforeEach(() => {
  vi.resetAllMocks();
});

test('meta function sets title', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
});

test('renders loaded templates', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      templates: [
        {
          id: 1,
          key: 'high_congestion',
          description: 'High congestion profile',
          date_created: '2026-03-29T00:00:00Z',
          date_updated: '2026-03-29T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/traffic-templates',
      Component: TrafficTemplates,
    },
  ]);

  render(<Stub initialEntries={['/traffic-templates']} />);

  expect(await screen.findByText('high_congestion')).toBeInTheDocument();
  expect(
    await screen.findByText('High congestion profile')
  ).toBeInTheDocument();
});

test('creates a template from CSV upload', async () => {
  const user = userEvent.setup();

  vi.mocked(api.get)
    .mockResolvedValueOnce({
      data: {
        templates: [],
        total: 0,
        page: 1,
        per_page: 20,
        total_pages: 0,
      },
    })
    .mockResolvedValueOnce({
      data: {
        templates: [
          {
            id: 2,
            key: 'new_template',
            description: 'Uploaded template',
            date_created: '2026-03-29T00:00:00Z',
            date_updated: '2026-03-29T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      },
    });

  vi.mocked(api.post)
    .mockResolvedValueOnce({
      data: {
        valid: true,
        errors: [],
      },
    })
    .mockResolvedValueOnce({
      data: {
        key: 'new_template',
      },
    });

  const Stub = createRoutesStub([
    {
      path: '/traffic-templates',
      Component: TrafficTemplates,
    },
  ]);

  const { container } = render(
    <Stub initialEntries={['/traffic-templates']} />
  );

  await screen.findByText('No traffic templates found.');

  const csvFile = new File(
    [
      'TYPE,start_time,segment_key,name,duration,weight\nlocal_traffic,08:00,"((0,0),(1,1))",x,60,0.8',
    ],
    'new_template.csv',
    { type: 'text/csv' }
  );

  const fileInputs = container.querySelectorAll('input[type="file"]');
  fireEvent.change(fileInputs[0], { target: { files: [csvFile] } });

  const keyInput = await screen.findByLabelText('Template key');
  fireEvent.change(keyInput, { target: { value: 'new_template' } });

  await user.click(screen.getByRole('button', { name: 'Upload template' }));

  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith('/trafficTemplates/validate', {
      content: expect.stringContaining('TYPE,start_time,segment_key'),
    });
  });

  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith('/trafficTemplates', {
      key: 'new_template',
      content: expect.stringContaining('TYPE,start_time,segment_key'),
      description: undefined,
    });
  });
});

test('rejects upload when extension is .csv but MIME type is invalid', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      templates: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 0,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/traffic-templates',
      Component: TrafficTemplates,
    },
  ]);

  const { container } = render(
    <Stub initialEntries={['/traffic-templates']} />
  );

  await screen.findByText('No traffic templates found.');

  const renamedNonCsvFile = new File(['not,csv'], 'renamed.csv', {
    type: 'image/png',
  });

  const fileInputs = container.querySelectorAll('input[type="file"]');
  fireEvent.change(fileInputs[0], { target: { files: [renamedNonCsvFile] } });

  expect(
    await screen.findByText('Please import a .csv file.')
  ).toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

test('accepts .csv upload when MIME type is empty', async () => {
  const user = userEvent.setup();

  vi.mocked(api.get)
    .mockResolvedValueOnce({
      data: {
        templates: [],
        total: 0,
        page: 1,
        per_page: 20,
        total_pages: 0,
      },
    })
    .mockResolvedValueOnce({
      data: {
        templates: [
          {
            id: 2,
            key: 'empty_mime_template',
            description: 'Uploaded template',
            date_created: '2026-03-29T00:00:00Z',
            date_updated: '2026-03-29T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      },
    });

  vi.mocked(api.post)
    .mockResolvedValueOnce({
      data: {
        valid: true,
        errors: [],
      },
    })
    .mockResolvedValueOnce({
      data: {
        key: 'empty_mime_template',
      },
    });

  const Stub = createRoutesStub([
    {
      path: '/traffic-templates',
      Component: TrafficTemplates,
    },
  ]);

  const { container } = render(
    <Stub initialEntries={['/traffic-templates']} />
  );

  await screen.findByText('No traffic templates found.');

  const csvFileWithEmptyMime = new File(
    [
      'TYPE,start_time,segment_key,name,duration,weight\nlocal_traffic,08:00,"((0,0),(1,1))",x,60,0.8',
    ],
    'empty_mime_template.csv',
    { type: '' }
  );

  const fileInputs = container.querySelectorAll('input[type="file"]');
  fireEvent.change(fileInputs[0], {
    target: { files: [csvFileWithEmptyMime] },
  });

  const keyInput = await screen.findByLabelText('Template key');
  fireEvent.change(keyInput, { target: { value: 'empty_mime_template' } });

  await user.click(screen.getByRole('button', { name: 'Upload template' }));

  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith('/trafficTemplates/validate', {
      content: expect.stringContaining('TYPE,start_time,segment_key'),
    });
  });

  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith('/trafficTemplates', {
      key: 'empty_mime_template',
      content: expect.stringContaining('TYPE,start_time,segment_key'),
      description: undefined,
    });
  });
});

test('rejects edit file replacement when extension is .csv but MIME type is invalid', async () => {
  const user = userEvent.setup();

  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      templates: [
        {
          id: 1,
          key: 'high_congestion',
          description: 'High congestion profile',
          date_created: '2026-03-29T00:00:00Z',
          date_updated: '2026-03-29T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/traffic-templates',
      Component: TrafficTemplates,
    },
  ]);

  const { container } = render(
    <Stub initialEntries={['/traffic-templates']} />
  );

  await screen.findByText('high_congestion');
  await user.click(screen.getByTestId('template-actions-high_congestion'));
  await user.click(screen.getByRole('menuitem', { name: /Edit/i }));

  const renamedNonCsvFile = new File(['not,csv'], 'renamed.csv', {
    type: 'image/png',
  });

  const fileInputs = container.querySelectorAll('input[type="file"]');
  fireEvent.change(fileInputs[1], { target: { files: [renamedNonCsvFile] } });

  await user.click(screen.getByRole('button', { name: /Update/i }));

  expect(
    await screen.findByText('Please import a .csv file.')
  ).toBeInTheDocument();
  expect(api.put).not.toHaveBeenCalled();
});

test('downloads template by fetching content on demand', async () => {
  const user = userEvent.setup();

  vi.mocked(api.get)
    .mockResolvedValueOnce({
      data: {
        templates: [
          {
            id: 1,
            key: 'high_congestion',
            description: 'High congestion profile',
            date_created: '2026-03-29T00:00:00Z',
            date_updated: '2026-03-29T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      },
    })
    .mockResolvedValueOnce({
      data: {
        id: 1,
        key: 'high_congestion',
        content: 'TYPE,start_time,segment_key,name,duration,weight',
        description: 'High congestion profile',
        date_created: '2026-03-29T00:00:00Z',
        date_updated: '2026-03-29T00:00:00Z',
      },
    });

  const createObjectURLSpy = vi
    .spyOn(URL, 'createObjectURL')
    .mockReturnValue('blob:download');
  const revokeObjectURLSpy = vi
    .spyOn(URL, 'revokeObjectURL')
    .mockImplementation(() => undefined);

  const appendChildSpy = vi.spyOn(document.body, 'appendChild');
  const removeChildSpy = vi.spyOn(document.body, 'removeChild');
  const clickSpy = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => undefined);

  const Stub = createRoutesStub([
    {
      path: '/traffic-templates',
      Component: TrafficTemplates,
    },
  ]);

  render(<Stub initialEntries={['/traffic-templates']} />);

  await screen.findByText('high_congestion');
  await user.click(screen.getByTestId('template-actions-high_congestion'));
  await user.click(screen.getByRole('menuitem', { name: /Download/i }));

  await waitFor(() => {
    expect(api.get).toHaveBeenCalledWith('/trafficTemplates/high_congestion');
  });

  expect(createObjectURLSpy).toHaveBeenCalledOnce();
  expect(revokeObjectURLSpy).toHaveBeenCalledOnce();
  expect(appendChildSpy).toHaveBeenCalled();
  expect(removeChildSpy).toHaveBeenCalled();
  expect(clickSpy).toHaveBeenCalledOnce();

  clickSpy.mockRestore();
  appendChildSpy.mockRestore();
  removeChildSpy.mockRestore();
  createObjectURLSpy.mockRestore();
  revokeObjectURLSpy.mockRestore();
});

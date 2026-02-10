import '@testing-library/jest-dom/vitest';
import { beforeEach, vi } from 'vitest';
import { mockDisplayError, MockMap } from './mocks';
import React from 'react';

// We mock useError to prevent actual error dialogs during tests - global error handling tests are in error-provider.test.tsx
vi.mock('~/hooks/use-error', () => {
  return {
    default: () => ({
      displayError: mockDisplayError,
    }),
  };
});

vi.mock(import('~/lib/logger'), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    log: vi.fn(),
  };
});

vi.mock('mapbox-gl', () => {
  return {
    default: {
      Map: MockMap,
    },
  };
});

// Mock CodeMirror to render as a simple textarea for testing
vi.mock('@uiw/react-codemirror', () => {
  return {
    default: ({
      value,
      onChange,
      extensions,
      editable = true,
      ...props
    }: {
      value?: string;
      onChange?: (value: string) => void;
      extensions?: unknown[];
      editable?: boolean;
      [key: string]: unknown;
    }) => {
      // Extract placeholder from extensions if present
      let placeholderText = 'Paste or type your JSON scenario here...';
      if (extensions) {
        const placeholderExt = extensions.find((ext: unknown) => {
          return (
            (ext as { facet?: { name?: string } })?.facet?.name ===
              'placeholder' ||
            (typeof ext === 'function' &&
              ext.toString().includes('placeholder'))
          );
        });
        if (placeholderExt) {
          try {
            // Try to extract placeholder text - it's usually in the extension definition
            const match = placeholderExt
              .toString()
              .match(/placeholder\(['"]([^'"]+)['"]\)/);
            if (match) {
              placeholderText = match[1];
            }
          } catch {
            // Use default
          }
        }
      }

      return React.createElement('textarea', {
        ...props,
        id: 'scenario-json', // Add ID to connect with label
        value: value || '',
        onChange: (e: { target: { value: string } }) =>
          onChange?.(e.target.value),
        disabled: !editable,
        placeholder: placeholderText,
        'data-testid': 'codemirror-mock',
      });
    },
  };
});

beforeEach(async () => {
  MockMap.clear();
});

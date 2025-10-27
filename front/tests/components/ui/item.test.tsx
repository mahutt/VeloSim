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

import { describe, expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  Item,
  ItemMedia,
  ItemContent,
  ItemTitle,
  ItemDescription,
  ItemActions,
  ItemGroup,
  ItemSeparator,
  ItemHeader,
  ItemFooter,
} from '~/components/ui/item';

describe('Item UI primitives', () => {
  test('renders Item with media, content, title, description and actions', () => {
    render(
      <Item data-testid="item-root">
        <ItemMedia data-testid="item-media">M</ItemMedia>
        <ItemContent>
          <ItemTitle data-testid="item-title">My title</ItemTitle>
          <ItemDescription data-testid="item-desc">
            A description
          </ItemDescription>
        </ItemContent>
        <ItemActions>
          <button type="button">Act</button>
        </ItemActions>
      </Item>
    );

    const root = screen.getByTestId('item-root');
    expect(root).toBeInTheDocument();
    expect(root).toHaveAttribute('data-slot', 'item');

    expect(screen.getByTestId('item-media')).toHaveAttribute(
      'data-slot',
      'item-media'
    );
    expect(screen.getByTestId('item-title')).toHaveAttribute(
      'data-slot',
      'item-title'
    );
    expect(screen.getByTestId('item-desc')).toHaveAttribute(
      'data-slot',
      'item-description'
    );
  });

  test('forwards props to child when using asChild', async () => {
    const user = userEvent.setup();
    render(
      <Item asChild>
        <a href="#" data-testid="as-child-link">
          Link
        </a>
      </Item>
    );

    const link = screen.getByTestId('as-child-link');
    expect(link).toHaveAttribute('data-slot', 'item');

    await user.click(link);
    expect(link).toBeInTheDocument();
  });

  test('applies variant and size attributes', () => {
    render(
      <Item variant="outline" size="sm" data-testid="item-variant">
        <ItemContent />
      </Item>
    );

    const el = screen.getByTestId('item-variant');
    expect(el).toHaveAttribute('data-variant', 'outline');
    expect(el).toHaveAttribute('data-size', 'sm');
  });
});

test('renders ItemGroup, ItemSeparator and item slots', () => {
  render(
    <ItemGroup data-testid="group-root">
      <Item data-testid="group-item-1">
        <ItemContent />
      </Item>
      <ItemSeparator data-testid="group-sep" />
      <Item data-testid="group-item-2">
        <ItemContent />
      </Item>
    </ItemGroup>
  );

  const group = screen.getByTestId('group-root');
  expect(group).toBeInTheDocument();
  expect(group).toHaveAttribute('role', 'list');
  expect(group).toHaveAttribute('data-slot', 'item-group');

  const sep = screen.getByTestId('group-sep');
  expect(sep).toBeInTheDocument();
  expect(sep).toHaveAttribute('data-slot', 'item-separator');
  expect(sep.getAttribute('data-orientation')).toBe('horizontal');
});

test('ItemMedia supports variants and forwards props to children', () => {
  render(
    <div>
      <ItemMedia data-testid="media-default">D</ItemMedia>
      <ItemMedia
        variant="icon"
        data-testid="media-icon"
        aria-label="icon-media"
      >
        <svg />
      </ItemMedia>
      <ItemMedia variant="image" data-testid="media-image">
        <img src="/foo.png" alt="img" />
      </ItemMedia>
    </div>
  );

  const mDefault = screen.getByTestId('media-default');
  expect(mDefault).toHaveAttribute('data-slot', 'item-media');
  expect(mDefault).toHaveAttribute('data-variant', 'default');

  const mIcon = screen.getByTestId('media-icon');
  expect(mIcon).toHaveAttribute('data-variant', 'icon');
  expect(mIcon).toHaveAttribute('aria-label', 'icon-media');

  const mImage = screen.getByTestId('media-image');
  expect(mImage).toHaveAttribute('data-variant', 'image');
  expect(mImage.querySelector('img')).toBeTruthy();
});

test('renders header, footer and actions slots correctly', () => {
  render(
    <Item data-testid="item-hf">
      <ItemHeader data-testid="item-header">
        <div>Left</div>
        <div>Right</div>
      </ItemHeader>
      <ItemContent>
        <ItemTitle>Title</ItemTitle>
        <ItemDescription>Description</ItemDescription>
      </ItemContent>
      <ItemFooter data-testid="item-footer">Footer</ItemFooter>
      <ItemActions data-testid="item-actions">
        <button type="button">Do</button>
      </ItemActions>
    </Item>
  );

  expect(screen.getByTestId('item-header')).toHaveAttribute(
    'data-slot',
    'item-header'
  );
  expect(screen.getByTestId('item-footer')).toHaveAttribute(
    'data-slot',
    'item-footer'
  );
  expect(screen.getByTestId('item-actions')).toHaveAttribute(
    'data-slot',
    'item-actions'
  );
  expect(screen.getByText('Title')).toBeInTheDocument();
  expect(screen.getByText('Description')).toBeInTheDocument();
});

test('ItemDescription renders links inside and keeps slot', () => {
  render(
    <ItemDescription data-testid="desc">
      Some text and <a href="#">a link</a>
    </ItemDescription>
  );

  const desc = screen.getByTestId('desc');
  expect(desc).toHaveAttribute('data-slot', 'item-description');
  expect(desc.querySelector('a')).toBeTruthy();
  expect(screen.getByText('a link')).toBeInTheDocument();
});

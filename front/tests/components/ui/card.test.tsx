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

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
  CardContent,
  CardFooter,
} from '~/components/ui/card';

describe('Card Components', () => {
  describe('Card', () => {
    it('should render card with default classes', () => {
      render(<Card data-testid="card">Card content</Card>);

      const card = screen.getByTestId('card');
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute('data-slot', 'card');
      expect(card.className).toContain('bg-card');
      expect(card.className).toContain('text-card-foreground');
      expect(card.className).toContain('flex');
      expect(card.className).toContain('flex-col');
      expect(card.className).toContain('gap-6');
      expect(card.className).toContain('rounded-xl');
      expect(card.className).toContain('border');
      expect(card.className).toContain('py-6');
      expect(card.className).toContain('shadow-sm');
    });

    it('should render card with custom className', () => {
      render(
        <Card className="custom-class" data-testid="card">
          Card content
        </Card>
      );

      const card = screen.getByTestId('card');
      expect(card.className).toContain('custom-class');
    });

    it('should render card with children', () => {
      render(<Card>Test card content</Card>);

      expect(screen.getByText('Test card content')).toBeInTheDocument();
    });
  });

  describe('CardHeader', () => {
    it('should render card header with default classes', () => {
      render(<CardHeader data-testid="card-header">Header content</CardHeader>);

      const header = screen.getByTestId('card-header');
      expect(header).toBeInTheDocument();
      expect(header).toHaveAttribute('data-slot', 'card-header');
      expect(header.className).toContain('@container/card-header');
      expect(header.className).toContain('grid');
      expect(header.className).toContain('auto-rows-min');
      expect(header.className).toContain('grid-rows-[auto_auto]');
      expect(header.className).toContain('items-start');
      expect(header.className).toContain('gap-2');
      expect(header.className).toContain('px-6');
    });

    it('should render card header with custom className', () => {
      render(
        <CardHeader className="custom-header" data-testid="card-header">
          Header
        </CardHeader>
      );

      const header = screen.getByTestId('card-header');
      expect(header.className).toContain('custom-header');
    });
  });

  describe('CardTitle', () => {
    it('should render card title with default classes', () => {
      render(<CardTitle data-testid="card-title">Title</CardTitle>);

      const title = screen.getByTestId('card-title');
      expect(title).toBeInTheDocument();
      expect(title).toHaveAttribute('data-slot', 'card-title');
      expect(title.className).toContain('leading-none');
      expect(title.className).toContain('font-semibold');
    });

    it('should render card title with custom className', () => {
      render(
        <CardTitle className="custom-title" data-testid="card-title">
          Title
        </CardTitle>
      );

      const title = screen.getByTestId('card-title');
      expect(title.className).toContain('custom-title');
    });
  });

  describe('CardDescription', () => {
    it('should render card description with default classes', () => {
      render(
        <CardDescription data-testid="card-description">
          Description
        </CardDescription>
      );

      const description = screen.getByTestId('card-description');
      expect(description).toBeInTheDocument();
      expect(description).toHaveAttribute('data-slot', 'card-description');
      expect(description.className).toContain('text-muted-foreground');
      expect(description.className).toContain('text-sm');
    });

    it('should render card description with custom className', () => {
      render(
        <CardDescription className="custom-desc" data-testid="card-description">
          Description
        </CardDescription>
      );

      const description = screen.getByTestId('card-description');
      expect(description.className).toContain('custom-desc');
    });
  });

  describe('CardAction', () => {
    it('should render card action with default classes', () => {
      render(<CardAction data-testid="card-action">Action</CardAction>);

      const action = screen.getByTestId('card-action');
      expect(action).toBeInTheDocument();
      expect(action).toHaveAttribute('data-slot', 'card-action');
      expect(action.className).toContain('col-start-2');
      expect(action.className).toContain('row-span-2');
      expect(action.className).toContain('row-start-1');
      expect(action.className).toContain('self-start');
      expect(action.className).toContain('justify-self-end');
    });

    it('should render card action with custom className', () => {
      render(
        <CardAction className="custom-action" data-testid="card-action">
          Action
        </CardAction>
      );

      const action = screen.getByTestId('card-action');
      expect(action.className).toContain('custom-action');
    });
  });

  describe('CardContent', () => {
    it('should render card content with default classes', () => {
      render(<CardContent data-testid="card-content">Content</CardContent>);

      const content = screen.getByTestId('card-content');
      expect(content).toBeInTheDocument();
      expect(content).toHaveAttribute('data-slot', 'card-content');
      expect(content.className).toContain('px-6');
    });

    it('should render card content with custom className', () => {
      render(
        <CardContent className="custom-content" data-testid="card-content">
          Content
        </CardContent>
      );

      const content = screen.getByTestId('card-content');
      expect(content.className).toContain('custom-content');
    });
  });

  describe('CardFooter', () => {
    it('should render card footer with default classes', () => {
      render(<CardFooter data-testid="card-footer">Footer</CardFooter>);

      const footer = screen.getByTestId('card-footer');
      expect(footer).toBeInTheDocument();
      expect(footer).toHaveAttribute('data-slot', 'card-footer');
      expect(footer.className).toContain('flex');
      expect(footer.className).toContain('items-center');
      expect(footer.className).toContain('px-6');
    });

    it('should render card footer with custom className', () => {
      render(
        <CardFooter className="custom-footer" data-testid="card-footer">
          Footer
        </CardFooter>
      );

      const footer = screen.getByTestId('card-footer');
      expect(footer.className).toContain('custom-footer');
    });
  });

  describe('Card composition', () => {
    it('should render full card with all components', () => {
      render(
        <Card data-testid="full-card">
          <CardHeader>
            <CardTitle>Test Title</CardTitle>
            <CardDescription>Test Description</CardDescription>
            <CardAction>Action Button</CardAction>
          </CardHeader>
          <CardContent>
            <p>This is the card content</p>
          </CardContent>
          <CardFooter>
            <span>Footer content</span>
          </CardFooter>
        </Card>
      );

      expect(screen.getByTestId('full-card')).toBeInTheDocument();
      expect(screen.getByText('Test Title')).toBeInTheDocument();
      expect(screen.getByText('Test Description')).toBeInTheDocument();
      expect(screen.getByText('Action Button')).toBeInTheDocument();
      expect(screen.getByText('This is the card content')).toBeInTheDocument();
      expect(screen.getByText('Footer content')).toBeInTheDocument();
    });
  });
});

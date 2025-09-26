import { vi } from 'vitest';

type eventType = 'move';

export class MockMap {
  static instance: undefined | MockMap;
  private container: string | HTMLElement;
  private center: [number, number];
  private zoom: number;
  private style: string;
  private callBacks: Record<eventType, Function> = { move: () => {} };
  constructor({
    container,
    center,
    zoom,
    style,
  }: {
    container: string | HTMLElement;
    center: [number, number];
    zoom: number;
    style: string;
  }) {
    MockMap.instance = this;
    this.center = center;
    this.zoom = zoom;
    this.style = style;
    this.container = container;
  }
  on = vi.fn((type: eventType, cb: Function) => {
    this.callBacks[type] = cb;
  });
  remove = vi.fn();
  getCenter = vi.fn(() => this.center);
  getZoom = vi.fn(() => this.zoom);
  move = () => {
    this.callBacks['move']();
  };
  static clear() {
    MockMap.instance = undefined;
  }
}

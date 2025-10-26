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

// Basic types
export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  is_enabled: boolean;
}

// Entity types

export interface Station {
  id: number;
  name: string;
  position: [number, number]; // [longitude, latitude]
  tasks: StationTask[];
}

export interface StationTask {
  stationId: number;
  type: 'battery_swap';
}

// API response types

export interface LoginForAccessTokenResponse {
  access_token: string;
  token_type: 'Bearer';
}

interface PaginatedResponse {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface GetStationsResponse extends PaginatedResponse {
  stations: Omit<Station, 'tasks'>[];
}

export interface GetUsersResponse extends PaginatedResponse {
  users: User[];
}

// Resource types
export interface Resource {
  id: number;
  position: [number, number];
  taskList: number[]; // list of task IDs
  route: {
    coordinates: [number, number][];
  };
}

// Selection types
export enum SelectedItemType {
  Station = 'station',
  Resource = 'resource',
}
export interface SelectedItem {
  type: SelectedItemType;
  value: Station | Resource;
}

// Scenario types
export interface Scenario {
  id: number;
  name: string;
  user_id: number;
  content: string;
  date_created: string;
  date_updated: string;
}

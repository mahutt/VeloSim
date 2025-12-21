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

// Simulation types

export type Position = [number, number]; // [longitude, latitude]

export interface Station {
  id: number;
  name: string;
  position: Position;
  taskIds: number[];
}

// scheduled tasks aren't sent from the backend anymore
type TaskState = 'open' | 'assigned' | 'inprogress' | 'closed';

export interface StationTask {
  id: number;
  stationId: number;
  state: TaskState;
  assignedDriverId: number | null;
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

export interface ListMySimulationsResponse extends PaginatedResponse {
  simulations: Simulation[];
}

export interface GetUsersResponse extends PaginatedResponse {
  users: User[];
}

export interface ScenarioListResponse extends PaginatedResponse {
  scenarios: Scenario[];
}

export interface InitializeSimulationResponse {
  sim_id: string;
  db_id: number;
  status: string;
}

export interface Driver {
  id: number;
  position: Position;
  taskIds: number[];
  route?: {
    coordinates: Position[];
  };
  inProgressTaskId: number | null;
  vehicleId: number | null; // null implies at HQ, not on route
}

export interface Vehicle {
  id: number;
  driverId: number | null; // null implies at HQ, not on route
  // inventory: number // will come later
}

// WebSocket connection types
export type SimulationStatus =
  | 'idle' // Not connected
  | 'connecting' // WebSocket connecting
  | 'loading' // Connected, waiting for initial frame
  | 'ready' // Initial frame received, can interact
  | 'running' // Frames streaming
  | 'error'; // Error state

export interface UseSimulationWebSocketOptions {
  simId: string | null;
  enabled: boolean; // Whether WebSocket should connect (e.g., map loaded && user authenticated)
  onInitialFrame: (payload: BackendPayload) => void;
  onFrameUpdate: (payload: BackendPayload) => void;
  onError: (title: string, message: string) => void;
}

export interface UseSimulationWebSocketReturn {
  isConnected: boolean;
  simulationStatus: SimulationStatus;
  wsRef: React.RefObject<WebSocket | null>;
}

// Scenario types
export interface Scenario {
  id: number;
  name: string;
  user_id: number;
  content: Record<string, unknown>; // JSON object from backend
  description?: string;
  date_created: string;
  date_updated: string;
  content_size?: number;
}

// Simulation types
export interface Simulation {
  id: number;
  user_id: number;
  date_created: string;
  date_updated: string;
  resource_count: number;
  station_count: number;
  task_count: number;
}

export interface BackendPayload {
  simId: string;
  tasks: StationTask[];
  stations: Station[];
  drivers: Driver[];
  vehicles: Vehicle[];
  clock: {
    simSecondsPassed: number;
    simMinutesPassed: number;
    realSecondsPassed: number;
    realMinutesPassed: number;
    startTime: number;
  };
}

// Task assignment types
export type TaskAction = 'assign' | 'reassign' | 'unassign';

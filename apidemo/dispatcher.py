#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
"""

VeloSim Automated Task Dispatcher

Uses the generated OpenAPI client for full type safety and IDE support.

Algorithm:
1. Fetch all OPEN tasks
2. Fetch all IDLE drivers
3. For each idle driver, assign the nearest open task
4. Wait and repeat

Press Ctrl+C to stop.

Prerequisites:
    Generated client (automatically created by setup.sh)
    Or run: python generate_client.py --local
"""

import os
import sys
import time
import getpass
import math
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Check if client is generated
client_path = Path(__file__).parent / "velosim_client"
if not client_path.exists():
    print("ERROR: Generated client not found!")
    print("Please run: python generate_client.py")
    sys.exit(1)

# Add client to Python path
sys.path.insert(0, str(client_path))

try:
    from velosim_client import AuthenticatedClient, Client
    from velosim_client.api.default import login_for_access_token_api_token_post
    from velosim_client.api.simulation import (
        get_simulation_tasks_api_v1_simulation_sim_id_tasks_get,
        get_simulation_drivers_api_v1_simulation_sim_id_drivers_get,
        assign_task_to_driver_api_v1_simulation_sim_id_drivers_assign_post,
    )
    from velosim_client.models import (
        BodyLoginForAccessTokenApiTokenPost,
        DriverTaskAssignRequest,
    )
    from velosim_client.types import Response
except ImportError as e:
    print(f"ERROR: Could not import generated client: {e}")
    print("Please run: python generate_client.py")
    sys.exit(1)


@dataclass
class Config:
    """Configuration for the dispatcher."""

    api_url: str
    username: str
    password: str
    sim_id: str
    poll_interval: float = 2.0


def prompt_for_config() -> Config:
    """Interactively prompt user for configuration.

    Returns:
        Config object with user inputs
    """
    print("VeloSim Automated Task Dispatcher (Type-Safe)")
    print("=" * 40)
    print()

    # API URL
    default_url = os.getenv("VELOSIM_API_URL", "https://velosim.app")
    api_url = input(f"VeloSim API URL [{default_url}]: ").strip()
    api_url = api_url or default_url

    # Username
    username = os.getenv("VELOSIM_USERNAME")
    if not username:
        username = input("Username: ").strip()
    else:
        print(f"Username: {username} (from env)")

    # Password
    password = os.getenv("VELOSIM_PASSWORD")
    if not password:
        password = getpass.getpass("Password: ")
    else:
        print("Password: (from env)")

    # Simulation ID
    sim_id = os.getenv("VELOSIM_SIM_ID")
    if not sim_id:
        sim_id = input("Simulation ID (UUID): ").strip()
    else:
        print(f"Simulation ID: {sim_id} (from env)")

    # Poll interval
    interval_str = os.getenv("POLL_INTERVAL", "2.0")
    poll_interval = float(interval_str)

    print()

    return Config(
        api_url=api_url,
        username=username,
        password=password,
        sim_id=sim_id,
        poll_interval=poll_interval,
    )


def authenticate(config: Config) -> AuthenticatedClient:
    """Authenticate with VeloSim API and create authenticated client.

    Args:
        config: Configuration with credentials

    Returns:
        Authenticated client instance

    Raises:
        SystemExit: If authentication fails
    """
    print("Authenticating...")

    # Create unauthenticated client for login
    temp_client = Client(base_url=config.api_url)

    try:
        # Call login endpoint
        login_data = BodyLoginForAccessTokenApiTokenPost(
            username=config.username,
            password=config.password,
        )

        response = login_for_access_token_api_token_post.sync_detailed(
            client=temp_client,
            body=login_data,
        )

        if response.status_code != 200 or not response.parsed:
            print(f"Authentication failed: {response.status_code}")
            if response.status_code == 400:
                print("Invalid username or password")
            sys.exit(1)

        token_data = response.parsed
        access_token = token_data.access_token

        print("Authentication successful!")

        # Create authenticated client
        client = AuthenticatedClient(
            base_url=config.api_url,
            token=access_token,
        )

        return client

    except Exception as e:
        print(f"Authentication error: {e}")
        sys.exit(1)


def calculate_distance(pos1: list[float], pos2: list[float]) -> float:
    """Calculate Euclidean distance between two positions.

    Args:
        pos1: [lat, lon] or [x, y]
        pos2: [lat, lon] or [x, y]

    Returns:
        Distance (simple Euclidean, good enough for nearest neighbor)
    """
    return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)


def find_nearest_task(driver: dict, tasks: list[dict]) -> Optional[dict]:
    """Find the nearest open task to a driver.

    Args:
        driver: Driver model with 'position' field
        tasks: List of task models with 'station' containing 'position'

    Returns:
        Nearest task or None if no tasks available
    """
    if not tasks:
        return None

    driver_pos = driver.get("position", [0, 0])

    nearest_task = None
    min_distance = float("inf")

    for task in tasks:
        station = task.get("station", {})
        station_pos = station.get("position", [0, 0])

        distance = calculate_distance(driver_pos, station_pos)

        if distance < min_distance:
            min_distance = distance
            nearest_task = task

    return nearest_task


def dispatch_loop(client: AuthenticatedClient, config: Config):
    """Main dispatching loop.

    Args:
        client: Authenticated client
        config: Configuration
    """
    print("Starting dispatcher...")
    print(f"Polling every {config.poll_interval} seconds")
    print("Press Ctrl+C to stop")
    print()

    iteration = 0
    total_assigned = 0

    # Track recently assigned task/driver pairs to avoid duplicate assignments
    # while backend state updates (eventual consistency)
    recently_assigned = {}  # {task_id: iteration_number}
    max_assignment_age = 5  # Remember assignments for 5 iterations (~10 seconds)

    try:
        while True:
            iteration += 1

            # Clean up old assignments from tracking
            recently_assigned = {
                task_id: iter_num
                for task_id, iter_num in recently_assigned.items()
                if iteration - iter_num < max_assignment_age
            }

            # Fetch open tasks
            tasks_response = (
                get_simulation_tasks_api_v1_simulation_sim_id_tasks_get.sync_detailed(
                    sim_id=config.sim_id,
                    client=client,
                    state="OPEN",
                    max_results=500,
                )
            )

            if tasks_response.status_code == 404:
                print("Simulation not found or completed")
                break
            elif tasks_response.status_code != 200 or not tasks_response.parsed:
                print(f"Failed to fetch tasks: {tasks_response.status_code}")
                time.sleep(config.poll_interval)
                continue

            # Fetch idle drivers
            drivers_response = get_simulation_drivers_api_v1_simulation_sim_id_drivers_get.sync_detailed(
                sim_id=config.sim_id,
                client=client,
                state="IDLE",
                max_results=500,
            )

            if drivers_response.status_code != 200 or not drivers_response.parsed:
                print(f"Failed to fetch drivers: {drivers_response.status_code}")
                time.sleep(config.poll_interval)
                continue

            # Convert to dicts for easier handling
            # (The generated models have to_dict() methods)
            open_tasks = [t.to_dict() for t in tasks_response.parsed.tasks]
            idle_drivers = [d.to_dict() for d in drivers_response.parsed.drivers]

            # Track assignments this round
            assigned_count = 0
            assigned_task_ids = set()

            # Assign nearest task to each idle driver
            for driver in idle_drivers:
                # Filter out already assigned tasks (this iteration + recently assigned)
                available_tasks = [
                    t
                    for t in open_tasks
                    if t["id"] not in assigned_task_ids
                    and t["id"] not in recently_assigned
                ]

                nearest_task = find_nearest_task(driver, available_tasks)

                if nearest_task:
                    # Create assignment request
                    assign_request = DriverTaskAssignRequest(
                        driver_id=driver["id"],
                        task_id=nearest_task["id"],
                    )

                    # Call assign endpoint
                    assign_response = assign_task_to_driver_api_v1_simulation_sim_id_drivers_assign_post.sync_detailed(
                        sim_id=config.sim_id,
                        client=client,
                        body=assign_request,
                    )

                    if assign_response.status_code == 200:
                        assigned_count += 1
                        total_assigned += 1
                        assigned_task_ids.add(nearest_task["id"])
                        recently_assigned[nearest_task["id"]] = iteration

                        station_name = nearest_task.get("station", {}).get("name", "?")
                        print(
                            f"Assigned task {nearest_task['id']} "
                            f"(station {station_name}) "
                            f"to driver {driver['id']}"
                        )
                    else:
                        print(
                            f"Failed to assign task {nearest_task['id']} "
                            f"to driver {driver['id']}: {assign_response.status_code}"
                        )

            # Display status
            print(
                f"[Iteration {iteration}] Open tasks: {len(open_tasks)}, "
                f"Idle drivers: {len(idle_drivers)}, "
                f"Assigned: {assigned_count}, "
                f"Total: {total_assigned}"
            )

            # Print summary
            if assigned_count == 0 and len(idle_drivers) > 0 and len(open_tasks) == 0:
                print("No open tasks available")
            elif assigned_count == 0 and len(idle_drivers) == 0:
                print("No idle drivers")

            # Check if simulation might be done
            if len(open_tasks) == 0 and len(idle_drivers) > 0:
                # Fetch all drivers to see if we're truly done
                all_drivers_response = get_simulation_drivers_api_v1_simulation_sim_id_drivers_get.sync_detailed(
                    sim_id=config.sim_id,
                    client=client,
                    max_results=500,
                )
                if all_drivers_response.parsed:
                    all_drivers_count = len(all_drivers_response.parsed.drivers)
                    if len(idle_drivers) == all_drivers_count:
                        print("All tasks assigned or completed!")
                        break

            # Wait before next iteration
            time.sleep(config.poll_interval)

    except KeyboardInterrupt:
        print()
        print("Dispatcher stopped by user")
    except Exception as e:
        print(f"Error in dispatch loop: {e}")
        import traceback

        traceback.print_exc()
        raise

    print()
    print(f"Total assignments made: {total_assigned}")
    print("Dispatcher finished")


def main():
    """Main entry point."""
    # Get configuration
    config = prompt_for_config()

    try:
        # Authenticate and get client
        client = authenticate(config)
        print()

        # Run dispatcher
        dispatch_loop(client, config)

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

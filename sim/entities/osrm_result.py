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

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OSRMStep:
    """
    Represents a single step (road segment) in an OSRM route.

    Each step corresponds to an actual road segment with its own
    characteristics like name, distance, duration, and geometry.

    Attributes:
        name: Street or road name (None if unnamed)
        distance: Length of this step in meters
        duration: Time to traverse this step in seconds
        geometry: List of [lon, lat] coordinate pairs defining the step's path
        speed: Maximum speed for this step in m/s (from OSRM annotations), optional
    """

    name: Optional[str]
    distance: float
    duration: float
    geometry: List[List[float]]
    speed: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OSRMStep":
        """
        Create an OSRMStep from OSRM API response data.

        Args:
            data: Dictionary from OSRM step data

        Returns:
            OSRMStep instance with validated data
        """
        # Handle both formats: geometry as list or as dict with coordinates key
        geometry = data.get("geometry", [])
        if isinstance(geometry, dict):
            geometry = geometry.get("coordinates", [])

        return cls(
            name=data.get("name") or None,
            distance=float(data.get("distance", 0.0)),
            duration=float(data.get("duration", 0.0)),
            geometry=geometry,
            speed=(
                float(data["speed"])
                if "speed" in data and data["speed"] is not None
                else None
            ),
        )


@dataclass
class OSRMResult:
    """
    Represents a complete route result from the OSRM routing engine.

    This class provides type-safe access to OSRM route data, eliminating
    the need for dict.get() fallbacks and null-island checks.

    Attributes:
        coordinates: Complete list of [lon, lat] waypoints for the entire route
        distance: Total route distance in meters
        duration: Total route duration in seconds
        steps: List of individual road segments that make up the route
    """

    coordinates: List[List[float]]
    distance: float
    duration: float
    steps: List[OSRMStep]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OSRMResult":
        """
        Create an OSRMResult from OSRM API response data.

        This factory method handles validation and type conversion,
        ensuring all required fields are present and properly typed.

        Args:
            data: Dictionary returned from OSRMConnection.shortest_path_coords()
                  Expected keys: 'coordinates', 'distance', 'duration', 'steps'

        Returns:
            OSRMResult instance with validated and typed data

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        # Validate required fields
        if "coordinates" not in data:
            raise ValueError("Missing required field: 'coordinates'")
        if "distance" not in data:
            raise ValueError("Missing required field: 'distance'")
        if "duration" not in data:
            raise ValueError("Missing required field: 'duration'")

        # Extract and validate coordinates
        coordinates = data["coordinates"]
        if not isinstance(coordinates, list):
            raise ValueError("'coordinates' must be a list")
        if not coordinates:
            raise ValueError("'coordinates' cannot be empty")

        # Convert distance and duration to floats
        try:
            distance = float(data["distance"])
            duration = float(data["duration"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid distance or duration: {e}")

        # Parse steps if present
        steps_data = data.get("steps", [])
        steps = [OSRMStep.from_dict(step) for step in steps_data]

        return cls(
            coordinates=coordinates,
            distance=distance,
            duration=duration,
            steps=steps,
        )

    @property
    def start_coord(self) -> tuple[float, float]:
        """Get the starting coordinate as a tuple (lon, lat)."""
        if not self.coordinates:
            return (0.0, 0.0)
        coord = self.coordinates[0]
        return (coord[0], coord[1])

    @property
    def end_coord(self) -> tuple[float, float]:
        """Get the ending coordinate as a tuple (lon, lat)."""
        if not self.coordinates:
            return (0.0, 0.0)
        coord = self.coordinates[-1]
        return (coord[0], coord[1])

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if not self.coordinates:
            raise ValueError("coordinates cannot be empty")
        if self.distance < 0:
            raise ValueError("distance cannot be negative")
        if self.duration < 0:
            raise ValueError("duration cannot be negative")

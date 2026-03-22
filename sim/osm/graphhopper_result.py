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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GraphHopperInstruction:
    """Single instruction in a GraphHopper route.

    Attributes:
        text: Human-readable instruction text
        distance: Distance in meters
        time: Time in milliseconds
        interval: [start_index, end_index] in route coordinates
        street_name: Optional street name for this segment
    """

    text: str
    distance: float
    time: float
    interval: List[int]
    street_name: Optional[str] = None


@dataclass
class GraphHopperSegment:
    """A segment of a GraphHopper route.

    Attributes:
        distance: Distance in meters
        duration: Duration in seconds
        geometry: List of [lon, lat] coordinates
        road_name: Optional name of the road
    """

    distance: float
    duration: float
    geometry: List[List[float]]
    road_name: Optional[str] = None


@dataclass
class GraphHopperResult:
    """Complete route result from GraphHopper API.

    Attributes:
        coordinates: List of [lon, lat] waypoints along route
        distance: Total distance in meters
        duration: Total duration in seconds
        instructions: List of turn-by-turn instructions
        segments: Route broken into segments
    """

    coordinates: List[List[float]]
    distance: float
    duration: float
    instructions: List[GraphHopperInstruction]
    segments: List[GraphHopperSegment] = field(default_factory=list)

    @classmethod
    def from_graphhopper_response(cls, response: Dict[str, Any]) -> "GraphHopperResult":
        """Parse GraphHopper API response into RouteResult.

        Args:
            response: JSON response from GraphHopper /route endpoint

        Returns:
            GraphHopperResult with parsed route data

        Raises:
            ValueError: If response is missing required fields
        """
        paths = response.get("paths")
        if not isinstance(paths, list) or not paths:
            raise ValueError("GraphHopper response missing 'paths'")

        path = paths[0]

        points = path.get("points", {})
        coordinates = points.get("coordinates", []) if isinstance(points, dict) else []

        distance = float(path.get("distance", 0.0))
        duration = float(path.get("time", 0.0)) / 1000.0

        raw_instructions = path.get("instructions", [])
        instructions: List[GraphHopperInstruction] = []
        for item in raw_instructions:
            interval = item.get("interval", [0, 0])
            if not isinstance(interval, list) or len(interval) < 2:
                interval = [0, 0]

            instructions.append(
                GraphHopperInstruction(
                    text=item.get("text", ""),
                    distance=float(item.get("distance", 0.0)),
                    time=float(item.get("time", 0.0)),
                    interval=[int(interval[0]), int(interval[1])],
                    street_name=item.get("street_name"),
                )
            )

        segments = cls._build_segments(instructions, coordinates)

        return cls(
            coordinates=coordinates,
            distance=distance,
            duration=duration,
            instructions=instructions,
            segments=segments,
        )

    @classmethod
    def _build_segments(
        cls,
        instructions: List[GraphHopperInstruction],
        coordinates: List[List[float]],
    ) -> List[GraphHopperSegment]:
        segments: List[GraphHopperSegment] = []
        for instruction in instructions:
            start_idx = max(0, instruction.interval[0])
            end_idx = min(len(coordinates) - 1, instruction.interval[1])
            if end_idx < start_idx or not coordinates:
                continue

            geometry = coordinates[start_idx : end_idx + 1]
            segments.append(
                GraphHopperSegment(
                    distance=instruction.distance,
                    duration=instruction.time / 1000.0,
                    geometry=geometry,
                    road_name=instruction.street_name,
                )
            )

        return segments

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
from typing import TYPE_CHECKING, Any, Optional
from grafana_logging.logger import get_logger

if TYPE_CHECKING:
    import simpy
    from sim.core.simulation_report import SimulationReport


logger = get_logger(__name__)


@dataclass
class TrafficConfig:
    """Configuration for traffic event loading.

    Attributes:
        traffic_level: Desired traffic level template to use.
        traffic_csv_data: Optional in-memory CSV content (for resume scenarios).
        sim_start_time: Start time of simulation.
        sim_end_time: End time of simulation.
    """

    traffic_level: str = "default"
    traffic_csv_data: Optional[str] = None
    sim_start_time: str = field(default="day1:00:00")
    sim_end_time: str = field(default="day1:00:00")


@dataclass
class MapPayload:
    """Configuration payload for map-related settings.

    Attributes:
        traffic: Optional traffic configuration.
        env: Optional SimPy environment for time-based operations.
        report: Optional simulation report for route metrics.
        route_recalculation_interval_minutes: Optional route refresh interval
            in minutes. Defaults to 30 when omitted.
        sim_id: Simulation ID.
    """

    DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES = 30

    traffic: Optional[TrafficConfig] = field(default=None)
    env: Optional["simpy.Environment"] = field(default=None)
    report: Optional["SimulationReport"] = field(default=None)
    route_recalculation_interval_minutes: Optional[int] = field(
        default=DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES
    )
    sim_id: str = field(default="")

    @classmethod
    def default_route_recalculation_interval_seconds(cls) -> int:
        """Return the default route recalculation interval in seconds.

        Args:
            cls: The MapPayload class.

        Returns:
            Default route recalculation interval in seconds (1800).
        """
        return cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES * 60

    @classmethod
    def normalize_route_recalculation_interval_minutes(cls, raw_value: Any) -> int:
        """Normalize route recalculation interval to a positive integer (minutes).

        Args:
            raw_value: Raw value to normalize, may be int/float/str/bool or other type.

        Returns:
            Normalized positive integer interval in minutes. Logs warning and returns
            default (30 minutes) for invalid or non-positive values.
        """
        if isinstance(raw_value, bool):
            logger.warning(
                "Invalid route_recalculation_interval_minutes=%r; using default %s",
                raw_value,
                cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES,
            )
            return cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES

        if isinstance(raw_value, float):
            if not raw_value.is_integer():
                logger.warning(
                    "Non-integer route_recalculation_interval_minutes=%r; "
                    "using default %s",
                    raw_value,
                    cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES,
                )
                return cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES
            minutes = int(raw_value)
        else:
            try:
                minutes = int(raw_value)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid route_recalculation_interval_minutes=%r; using default %s",
                    raw_value,
                    cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES,
                )
                return cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES

        if minutes <= 0:
            logger.warning(
                "Non-positive route_recalculation_interval_minutes=%s; "
                "using default %s",
                minutes,
                cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES,
            )
            return cls.DEFAULT_ROUTE_RECALCULATION_INTERVAL_MINUTES

        return minutes

    @classmethod
    def normalize_route_recalculation_interval_seconds(cls, raw_value: Any) -> int:
        """Normalize route recalculation interval to a positive integer (seconds).

        Args:
            raw_value: Raw value to normalize, may be int/float/str or other type.

        Returns:
            Normalized positive integer interval in seconds. Logs warning and returns
            default (1800 seconds) for invalid or non-positive values.
        """
        default_interval_seconds = cls.default_route_recalculation_interval_seconds()
        try:
            seconds = int(raw_value)
        except (TypeError, ValueError):
            logger.warning(
                "Invalid route_recalculation_interval_seconds=%r; "
                "using default %s seconds",
                raw_value,
                default_interval_seconds,
            )
            return default_interval_seconds

        if seconds <= 0:
            logger.warning(
                "Non-positive route_recalculation_interval_seconds=%s; "
                "using default %s seconds",
                seconds,
                default_interval_seconds,
            )
            return default_interval_seconds

        return seconds

    def get_route_recalculation_interval_seconds(self) -> int:
        """Get normalized route recalculation interval in seconds from payload.

        Returns:
            Normalized route recalculation interval in seconds from the payload's
            route_recalculation_interval_minutes field.
        """
        interval_minutes = self.normalize_route_recalculation_interval_minutes(
            self.route_recalculation_interval_minutes
        )
        return interval_minutes * 60

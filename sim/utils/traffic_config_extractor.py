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

import re
from typing import Any, Dict, Optional
from sim.entities.map_payload import TrafficConfig


TRAFFIC_TEMPLATE_KEY_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


def extract_traffic_config(
    scenario_content: Dict[str, Any],
    traffic_csv_data: Optional[str] = None,
) -> Optional[TrafficConfig]:
    """Extract TrafficConfig from scenario content dict.

    Used by both JsonParseStrategy (initial run) and ReplayParser
    (resume). Supports template-based traffic (traffic_level).

    Args:
        scenario_content: The scenario content dict
            (with start_time, end_time, traffic).
        traffic_csv_data: Optional in-memory CSV content
            (for resume scenarios).

    Returns:
        TrafficConfig if traffic configuration is present, None otherwise.

    Raises:
        ValueError: If traffic_level is not a valid template key.
    """
    traffic_raw = scenario_content.get("traffic", None)
    if traffic_raw is not None and isinstance(traffic_raw, dict):
        # Support template-based traffic (traffic_level)
        traffic_level = str(traffic_raw.get("traffic_level", "default"))
        gps_sync_delay = traffic_raw.get("gps_sync_delay", 10)

        # Get global field if exists
        global_field = traffic_raw.get("global", [])

        # Don't create config for "no_traffic" and global field empty
        if traffic_level == "no_traffic":
            if not global_field:
                return None
            traffic_level = None

        # Validate template key format for DB-backed lookup.
        if not TRAFFIC_TEMPLATE_KEY_PATTERN.fullmatch(traffic_level):
            raise ValueError(
                "traffic_level must be lowercase alphanumeric with "
                f"underscores/hyphens (1-32 chars), got '{traffic_level}'"
            )

        return TrafficConfig(
            traffic_level=traffic_level,
            traffic_csv_data=traffic_csv_data,
            global_schedule=global_field,
            sim_start_time=str(scenario_content.get("start_time", "day1:00:00")),
            sim_end_time=str(scenario_content.get("end_time", "day1:00:00")),
            gps_sync_delay=gps_sync_delay,
        )
    # Even without a traffic block in scenario, if we have persisted csv data,
    # we should still create a config (backwards compat for older scenarios)
    if traffic_csv_data:
        return TrafficConfig(
            traffic_level="default",
            traffic_csv_data=traffic_csv_data,
            sim_start_time=str(scenario_content.get("start_time", "day1:00:00")),
            sim_end_time=str(scenario_content.get("end_time", "day1:00:00")),
            gps_sync_delay=10,
        )
    return None

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

import ast
import sys
from typing import Tuple
import pandas as pd
import numpy as np
from grafana_logging.logger import get_logger

logger = get_logger(__name__)

# [min_lat, max_lat, min_lon, max_lon]
BRIDGE_GATEWAYS = {
    "champlain": [45.450, 45.480, -73.570, -73.540],
    "jacques_cartier": [45.515, 45.535, -73.560, -73.535],
    "mercier": [45.410, 45.440, -73.680, -73.640],
    "tunnel_lh": [45.570, 45.600, -73.520, -73.490],
    "victoria": [45.475, 45.495, -73.560, -73.530],
    "pont_viau": [45.545, 45.565, -73.685, -73.655],
    "lachapelle": [45.520, 45.545, -73.740, -73.710],
}


def get_segment_coords(
    segment_key: str,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Parses a raw segment key to get its coordinates.

    Args:
        segment_key: Raw string formatof a segment_key

    Returns:
        SegmentKey tuple: ((lon1, lat1), (lon2, lat2))

    Raises:
        ValueError: If the format is invalid.
    """
    try:
        parsed = ast.literal_eval(segment_key)
    except (ValueError, SyntaxError):
        raise ValueError(
            f"Invalid segment_key format: '{segment_key}'. "
            f"Expected format: ((lon1,lat1),(lon2,lat2))"
        )

    try:
        lon1, lat1 = float(parsed[0][0]), float(parsed[0][1])
        lon2, lat2 = float(parsed[1][0]), float(parsed[1][1])
    except (TypeError, ValueError):
        raise ValueError(f"segment_key coordinates must be numeric, got: {segment_key}")

    return (lon1, lat1), (lon2, lat2)


def is_bridge_involved(segment_key: str) -> bool:
    """
    Determines if a segment is within a bridge box range.

    Args:
        segment_key: Raw string format of a row segment_key

    Returns:
        True if start or end within a bridge box, otherwise False
    """
    start, end = get_segment_coords(segment_key)
    start_lon, start_lat = start
    end_lon, end_lat = end

    for box in BRIDGE_GATEWAYS.values():
        # check if start in box
        start_in = box[0] <= start_lat <= box[1] and box[2] <= start_lon <= box[3]
        # check if end in box
        end_in = box[0] <= end_lat <= box[1] and box[2] <= end_lon <= box[3]

        if start_in or end_in:
            return True
    return False


def get_probability_multiplier(time: str) -> float:
    """
    Determines probability boost according to when a traffic event is situated
    in time.

    Args:
        time: Raw string format of start_time of a traffic event

    Returns:
        Probability multiplier according to start time.
    """
    try:
        hour = int(time.split(":")[0])
        # if during peak hours (rush hours), increase likelihood of weight shift
        if (7 <= hour <= 9) or (15 <= hour <= 18):
            return 1.2
        # if very early morning, decrease likelihood of shift
        elif 0 <= hour <= 5:
            return 0.5
        return 1.0
    except Exception:
        return 1.0


def generate_template(
    df: pd.DataFrame, level: str, base_probability: float
) -> pd.DataFrame:
    """
    Creates a template for a given congestion level by possibly shifting
    weights within target ranges and applying bridge penalties.

    Args:
        df: Original Montreal traffic dataframe
        level: Congestion level to generate the template on
        base_probability: Probability of a row having a new weight value

    Returns:
        A template dataset with the new affected weights
    """
    template = df.copy()
    level_ranges = {
        "high_congestion": (0.1, 0.4),
        "medium_congestion": (0.4, 0.8),
        "low_congestion": (0.8, 1),
    }
    low_bound, high_bound = level_ranges[level]

    def get_row_weight(row) -> float:
        """Determines new weight of a specific row."""
        boost = get_probability_multiplier(row["start_time"])
        final_prob = min(0.9, base_probability * boost)

        # checks if row will keep its original weight
        if np.random.random() > final_prob:
            return row["weight"]

        is_bridge = is_bridge_involved(row["segment_key"])

        new_weight = np.random.uniform(low_bound, high_bound)
        if is_bridge:
            # adds a bridge penalty for Bridge Effect
            if level == "high_congestion":
                new_weight *= 0.3
            elif level == "medium_congestion":
                new_weight *= 0.6
        return new_weight

    template["weight"] = template.apply(get_row_weight, axis=1)

    return template


try:
    traffic_csv = "sim/traffic/traffic_datasets/traffic.csv"
    df = pd.read_csv(traffic_csv)

    # higher the congestion, higher the probability for more wide spread congestion
    level_to_base_probability = {
        "high_congestion": 0.8,
        "medium_congestion": 0.6,
        "low_congestion": 0.35,
    }

    for level, prob in level_to_base_probability.items():
        template = generate_template(df, level, prob)

        # save to csv
        filename = f"sim/traffic/traffic_datasets/{level}.csv"
        template.to_csv(filename, index=False)

except Exception as e:
    logger.error(f"Failed to generate template csv: {e}")
    sys.exit(1)

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

from typing import Any


def validate_longitude(v: Any) -> float:
    """Validate that longitude is between -180 and 180.

    Args:
        v: The longitude value to validate.

    Returns:
        float: Validated longitude value.
    """
    if not -180 <= v <= 180:
        raise ValueError("Longitude must be between -180 and 180")
    return float(v)


def validate_latitude(v: Any) -> float:
    """Validate that latitude is between -90 and 90.

    Args:
        v: The latitude value to validate.

    Returns:
        float: Validated latitude value.
    """
    if not -90 <= v <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    return float(v)


def validate_unique_task_ids(task_ids: Any) -> list[int]:
    """Validate that a sequence of task IDs contains no duplicates.

    Args:
        task_ids: Sequence of task IDs to validate.

    Returns:
        The same list of task IDs (as list[int]) when valid.

    Raises:
        ValueError: If duplicate IDs are found.
    """
    if task_ids is None:
        return []
    try:
        lst = list(task_ids)
    except TypeError:
        raise ValueError("task_ids must be a list of integers")

    if len(set(lst)) != len(lst):
        raise ValueError("Duplicate task_id in request")

    return lst

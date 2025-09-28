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

from typing import Optional

# Simple Hello World module for simulation


def hello_sim() -> str:
    """Return a greeting message from simulation."""
    return "Hello from VeloSim simulation!"


def get_sim_info() -> dict:
    """Return information about the simulation."""
    return {
        "name": "VeloSim Simulation Engine",
        "version": "1.0.0",
        "status": "active",
        "components": ["physics", "renderer", "api"],
    }


def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


def calculate_area(length: float, width: float) -> float:
    """Calculate the area of a rectangle."""
    if length <= 0 or width <= 0:
        raise ValueError("Length and width must be positive numbers")
    return length * width


def format_greeting(name: str) -> str:
    """Format a personalized greeting."""
    if not name or not name.strip():
        return "Hello, anonymous user!"
    return f"Hello, {name.strip()}!"


def process_data(data: list) -> dict:
    """Process a list of data and return summary statistics."""
    if not data:
        return {"count": 0, "sum": 0, "average": 0}

    total = sum(data)
    count = len(data)
    average = total / count

    return {
        "count": count,
        "sum": total,
        "average": average,
        "min": min(data),
        "max": max(data),
    }


def validate_config(config: dict) -> bool:
    """Validate simulation configuration."""
    required_keys = ["simulation_time", "time_step", "output_frequency"]
    return all(key in config for key in required_keys)


class SimulationGreeter:
    """A class to manage simulation greetings."""

    def __init__(self, default_name: str = "VeloSim User"):
        self.default_name = default_name
        self.greeting_count = 0

    def greet(self, name: Optional[str] = None) -> str:
        """Generate a greeting message."""
        self.greeting_count += 1
        target_name = name or self.default_name
        return f"Simulation greeting #{self.greeting_count}: " f"Hello, {target_name}!"

    def get_greeting_count(self) -> int:
        """Return the number of greetings generated."""
        return self.greeting_count

    def reset_count(self) -> None:
        """Reset the greeting counter."""
        self.greeting_count = 0

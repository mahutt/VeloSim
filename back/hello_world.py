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

# Simple Hello World module for backend API

from typing import Dict, List, Any


def hello_api() -> str:
    """Return a greeting message from the backend API."""
    return "Hello from VeloSim backend API!"


def get_api_status() -> Dict[str, Any]:
    """Return the current status of the API."""
    return {
        "service": "VeloSim Backend API",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": ["hello", "status", "health"],
    }


def health_check() -> Dict[str, Any]:
    """Perform a basic health check."""
    return {
        "healthy": True,
        "timestamp": "2025-01-01T00:00:00Z",
        "uptime": "running",
    }


def process_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a simple request with basic validation."""
    if not isinstance(data, dict):
        raise ValueError("Request data must be a dictionary")

    processed_data = {
        "original": data,
        "processed": True,
        "items_count": len(data),
    }
    return processed_data


def validate_user_input(user_input: str) -> bool:
    """Validate user input - check if it's not empty and reasonable length."""
    cleaned_input = user_input.strip()
    return len(cleaned_input) > 0 and len(cleaned_input) <= 1000


def format_response(message: str, success: bool = True) -> Dict[str, Any]:
    """Format a standardized API response."""
    return {
        "message": message,
        "success": success,
        "timestamp": "2025-01-01T00:00:00Z",
    }


def calculate_sum(numbers: List[float]) -> float:
    """Calculate the sum of a list of numbers."""
    if not isinstance(numbers, list):
        raise TypeError("Input must be a list")

    if not numbers:
        return 0.0

    total = 0.0
    for num in numbers:
        if not isinstance(num, (int, float)):
            raise ValueError(f"All items must be numbers, got {type(num)}")
        total += num

    return total


class APIManager:
    """A simple class to manage API operations."""

    def __init__(self, api_name: str = "VeloSim API"):
        self.api_name = api_name
        self.request_count = 0
        self.is_active = True

    def process_request(self, request_type: str) -> Dict[str, Any]:
        """Process different types of requests."""
        if not self.is_active:
            raise RuntimeError("API is not active")

        self.request_count += 1

        response = {
            "api_name": self.api_name,
            "request_type": request_type,
            "request_number": self.request_count,
            "status": "processed",
        }
        return response

    def get_stats(self) -> Dict[str, Any]:
        """Return API statistics."""
        return {
            "api_name": self.api_name,
            "total_requests": self.request_count,
            "is_active": self.is_active,
        }

    def deactivate(self) -> None:
        """Deactivate the API."""
        self.is_active = False

    def activate(self) -> None:
        """Activate the API."""
        self.is_active = True

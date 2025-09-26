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

import pytest
from typing import Dict, Any

from back.hello_world import (
    hello_api,
    get_api_status,
    health_check,
    process_request,
    validate_user_input,
    format_response,
    calculate_sum,
    APIManager,
)


class TestHelloApi:
    """Tests for the hello_api function"""

    def test_hello_api_returns_string(self) -> None:
        """Test that hello_api returns expected string"""
        result = hello_api()
        assert result == "Hello from VeloSim backend API!"
        assert isinstance(result, str)


class TestGetApiStatus:
    """Tests for the get_api_status function"""

    def test_get_api_status_structure(self) -> None:
        """Test that get_api_status returns correct structure"""
        result = get_api_status()
        assert isinstance(result, dict)
        assert "service" in result
        assert "version" in result
        assert "status" in result
        assert "endpoints" in result

    def test_get_api_status_values(self) -> None:
        """Test that get_api_status returns expected values"""
        result = get_api_status()
        assert result["service"] == "VeloSim Backend API"
        assert result["version"] == "1.0.0"
        assert result["status"] == "healthy"
        assert isinstance(result["endpoints"], list)


class TestHealthCheck:
    """Tests for the health_check function"""

    def test_health_check_structure(self) -> None:
        """Test that health_check returns correct structure"""
        result = health_check()
        assert isinstance(result, dict)
        assert "healthy" in result
        assert "timestamp" in result
        assert "uptime" in result

    def test_health_check_values(self) -> None:
        """Test that health_check returns expected values"""
        result = health_check()
        assert result["healthy"] is True
        assert isinstance(result["timestamp"], str)
        assert result["uptime"] == "running"


class TestProcessRequest:
    """Tests for the process_request function"""

    def test_process_request_valid_dict(self) -> None:
        """Test processing valid dictionary input"""
        test_data = {"key": "value", "number": 42}
        result = process_request(test_data)

        assert isinstance(result, dict)
        assert "original" in result
        assert "processed" in result
        assert "items_count" in result
        assert result["original"] == test_data
        assert result["processed"] is True
        assert result["items_count"] == 2

    def test_process_request_empty_dict(self) -> None:
        """Test processing empty dictionary"""
        test_data: Dict[str, Any] = {}
        result = process_request(test_data)

        assert result["original"] == test_data
        assert result["items_count"] == 0

    def test_process_request_invalid_input(self) -> None:
        """Test processing invalid input raises ValueError"""
        with pytest.raises(ValueError, match="Request data must be a dictionary"):
            process_request("not a dict")  # type: ignore[arg-type]


class TestValidateUserInput:
    """Tests for the validate_user_input function"""

    def test_validate_valid_input(self) -> None:
        """Test validating valid user input"""
        assert validate_user_input("valid input") is True
        assert validate_user_input("another valid input") is True

    def test_validate_empty_input(self) -> None:
        """Test validating empty input"""
        assert validate_user_input("") is False
        assert validate_user_input("   ") is False

    def test_validate_long_input(self) -> None:
        """Test validating very long input"""
        long_input = "x" * 1001
        assert validate_user_input(long_input) is False

    def test_validate_max_length_input(self) -> None:
        """Test validating input at max length"""
        max_length_input = "x" * 1000
        assert validate_user_input(max_length_input) is True


class TestFormatResponse:
    """Tests for the format_response function"""

    def test_format_response_success_default(self) -> None:
        """Test formatting response with default success"""
        result = format_response("Test message")
        assert result["message"] == "Test message"
        assert result["success"] is True
        assert "timestamp" in result

    def test_format_response_success_explicit(self) -> None:
        """Test formatting response with explicit success"""
        result = format_response("Success message", True)
        assert result["message"] == "Success message"
        assert result["success"] is True

    def test_format_response_failure(self) -> None:
        """Test formatting response with failure"""
        result = format_response("Error message", False)
        assert result["message"] == "Error message"
        assert result["success"] is False


class TestCalculateSum:
    """Tests for the calculate_sum function"""

    def test_calculate_sum_empty_list(self) -> None:
        """Test sum calculation with empty list"""
        result = calculate_sum([])
        assert result == 0.0

    def test_calculate_sum_positive_numbers(self) -> None:
        """Test sum calculation with positive numbers"""
        result = calculate_sum([1.0, 2.5, 3.0])
        assert result == 6.5

    def test_calculate_sum_negative_numbers(self) -> None:
        """Test sum calculation with negative numbers"""
        result = calculate_sum([-1.0, -2.5, -3.0])
        assert result == -6.5

    def test_calculate_sum_mixed_numbers(self) -> None:
        """Test sum calculation with mixed numbers"""
        result = calculate_sum([-5.0, 10.0, -3.0])
        assert result == 2.0

    def test_calculate_sum_invalid_input_string(self) -> None:
        """Test sum calculation with invalid string input"""
        with pytest.raises(TypeError, match="Input must be a list"):
            calculate_sum("not a list")  # type: ignore[arg-type]

    def test_calculate_sum_invalid_input_number(self) -> None:
        """Test sum calculation with invalid number input"""
        with pytest.raises(TypeError, match="Input must be a list"):
            calculate_sum(123)  # type: ignore[arg-type]

    def test_calculate_sum_invalid_list_items(self) -> None:
        """Test sum calculation with invalid items in list"""
        with pytest.raises(ValueError, match="All items must be numbers"):
            calculate_sum([1.0, "invalid", 3.0])  # type: ignore[list-item]


class TestAPIManager:
    """Tests for the APIManager class"""

    def test_init_default(self) -> None:
        """Test APIManager initialization with defaults"""
        manager = APIManager()
        assert manager.api_name == "VeloSim API"
        assert manager.request_count == 0
        assert manager.is_active is True

    def test_init_custom_name(self) -> None:
        """Test APIManager initialization with custom name"""
        manager = APIManager("Custom API")
        assert manager.api_name == "Custom API"
        assert manager.request_count == 0
        assert manager.is_active is True

    def test_process_request_when_active(self) -> None:
        """Test processing request when API is active"""
        manager = APIManager("Test API")
        result = manager.process_request("GET")

        assert isinstance(result, dict)
        assert result["api_name"] == "Test API"
        assert result["request_type"] == "GET"
        assert result["request_number"] == 1
        assert result["status"] == "processed"
        assert manager.request_count == 1

    def test_process_request_when_inactive(self) -> None:
        """Test processing request when API is inactive"""
        manager = APIManager("Test API")
        manager.deactivate()

        with pytest.raises(RuntimeError, match="API is not active"):
            manager.process_request("GET")

    def test_get_stats(self) -> None:
        """Test getting API statistics"""
        manager = APIManager("Stats API")
        manager.process_request("GET")
        manager.process_request("POST")

        stats = manager.get_stats()
        assert stats["api_name"] == "Stats API"
        assert stats["total_requests"] == 2
        assert stats["is_active"] is True

    def test_deactivate_activate(self) -> None:
        """Test deactivating and activating API"""
        manager = APIManager("Toggle API")

        # Initially active
        assert manager.is_active

        # Deactivate
        manager.deactivate()
        active_status: bool = manager.is_active
        assert active_status == False

        # Activate again
        manager.activate()
        assert manager.is_active

    def test_stats_after_deactivation(self) -> None:
        """Test getting stats after deactivation"""
        manager = APIManager("Deactivated API")
        manager.process_request("GET")
        manager.deactivate()

        stats = manager.get_stats()
        assert stats["total_requests"] == 1
        assert stats["is_active"] == False  # Keep explicit for MyPy

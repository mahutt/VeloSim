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
from sim.hello_world import (
    hello_sim,
    get_sim_info,
    add_numbers,
    multiply_numbers,
    calculate_area,
    format_greeting,
    process_data,
    validate_config,
    SimulationGreeter,
)


class TestBasicFunctions:
    """Test basic hello world functions."""

    def test_hello_sim(self) -> None:
        """Test hello_sim function."""
        result = hello_sim()
        assert result == "Hello from VeloSim simulation!"
        assert isinstance(result, str)

    def test_get_sim_info(self) -> None:
        """Test get_sim_info function."""
        info = get_sim_info()
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "status" in info
        assert "components" in info
        assert info["name"] == "VeloSim Simulation Engine"
        assert info["version"] == "1.0.0"


class TestMathFunctions:
    """Test mathematical calculation functions."""

    def test_add_numbers(self) -> None:
        """Test add_numbers function."""
        assert add_numbers(2.0, 3.0) == 5.0
        assert add_numbers(-1.0, 1.0) == 0.0
        assert add_numbers(0.1, 0.2) == pytest.approx(0.3)

    def test_multiply_numbers(self) -> None:
        """Test multiply_numbers function."""
        assert multiply_numbers(2.0, 3.0) == 6.0
        assert multiply_numbers(-2.0, 3.0) == -6.0
        assert multiply_numbers(0.0, 5.0) == 0.0

    def test_calculate_area_valid(self) -> None:
        """Test calculate_area with valid inputs."""
        assert calculate_area(3.0, 4.0) == 12.0
        assert calculate_area(2.5, 2.0) == 5.0

    def test_calculate_area_invalid(self) -> None:
        """Test calculate_area with invalid inputs."""
        with pytest.raises(ValueError):
            calculate_area(0, 5)
        with pytest.raises(ValueError):
            calculate_area(5, -1)
        with pytest.raises(ValueError):
            calculate_area(-1, -1)


class TestStringFunctions:
    """Test string processing functions."""

    def test_format_greeting_valid(self) -> None:
        """Test format_greeting with valid names."""
        assert format_greeting("Alice") == "Hello, Alice!"
        assert format_greeting("  Bob  ") == "Hello, Bob!"

    def test_format_greeting_invalid(self) -> None:
        """Test format_greeting with invalid inputs."""
        assert format_greeting("") == "Hello, anonymous user!"
        assert format_greeting("   ") == "Hello, anonymous user!"


class TestDataProcessing:
    """Test data processing functions."""

    def test_process_data_valid(self) -> None:
        """Test process_data with valid data."""
        result = process_data([1, 2, 3, 4, 5])
        assert result["count"] == 5
        assert result["sum"] == 15
        assert result["average"] == 3.0
        assert result["min"] == 1
        assert result["max"] == 5

    def test_process_data_empty(self) -> None:
        """Test process_data with empty data."""
        result = process_data([])
        assert result["count"] == 0
        assert result["sum"] == 0
        assert result["average"] == 0

    def test_validate_config_valid(self) -> None:
        """Test validate_config with valid configuration."""
        config = {
            "simulation_time": 100,
            "time_step": 0.01,
            "output_frequency": 10,
        }
        assert validate_config(config) is True

    def test_validate_config_invalid(self) -> None:
        """Test validate_config with invalid configuration."""
        config = {
            "simulation_time": 100,
            "time_step": 0.01,
            # missing output_frequency
        }
        assert validate_config(config) is False


class TestSimulationGreeterClass:
    """Test the SimulationGreeter class."""

    def test_simulation_greeter_creation(self) -> None:
        """Test SimulationGreeter instantiation."""
        greeter = SimulationGreeter("Test User")
        assert greeter.default_name == "Test User"
        assert greeter.greeting_count == 0

    def test_simulation_greeter_default_name(self) -> None:
        """Test SimulationGreeter with default name."""
        greeter = SimulationGreeter()
        assert greeter.default_name == "VeloSim User"

    def test_greet_with_name(self) -> None:
        """Test greeting with a specific name."""
        greeter = SimulationGreeter()
        result = greeter.greet("Alice")
        assert "Alice" in result
        assert "Simulation greeting #1" in result
        assert greeter.greeting_count == 1

    def test_greet_without_name(self) -> None:
        """Test greeting without a name (uses default)."""
        greeter = SimulationGreeter("Default User")
        result = greeter.greet()
        assert "Default User" in result
        assert "Simulation greeting #1" in result

    def test_greeting_counter(self) -> None:
        """Test that greeting counter increments properly."""
        greeter = SimulationGreeter()
        greeter.greet("User1")
        greeter.greet("User2")
        assert greeter.get_greeting_count() == 2

    def test_reset_count(self) -> None:
        """Test resetting the greeting counter."""
        greeter = SimulationGreeter()
        greeter.greet("User")
        greeter.greet("User")
        assert greeter.get_greeting_count() == 2

        greeter.reset_count()
        assert greeter.get_greeting_count() == 0

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

from sim.utils.traffic_config_extractor import extract_traffic_config
from sim.entities.map_payload import TrafficConfig


class TestExtractTrafficConfig:
    """Tests for extract_traffic_config utility function."""

    def test_extract_from_scenario_with_traffic_block(self) -> None:
        """Test extracting traffic config from scenario with traffic block."""
        scenario_content = {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
            "traffic": {"traffic_level": "high_congestion"},
        }

        config = extract_traffic_config(scenario_content)

        assert config is not None
        assert isinstance(config, TrafficConfig)
        assert config.traffic_level == "high_congestion"
        assert config.sim_start_time == "day1:08:00"
        assert config.sim_end_time == "day1:17:00"
        assert config.traffic_csv_data is None

    def test_extract_with_in_memory_csv_data(self) -> None:
        """Test extracting traffic config with in-memory CSV data."""
        scenario_content = {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
            "traffic": {"traffic_level": "medium_congestion"},
        }
        csv_data = "TYPE,start_time,segment_key,name,duration,weight\n"

        config = extract_traffic_config(scenario_content, traffic_csv_data=csv_data)

        assert config is not None
        assert config.traffic_level == "medium_congestion"
        assert config.traffic_csv_data == csv_data
        assert config.sim_start_time == "day1:08:00"
        assert config.sim_end_time == "day1:17:00"

    def test_extract_without_traffic_block_returns_none(self) -> None:
        """Test that scenarios without traffic block return None.

        The extractor is intentionally neutral — callers that need a default
        (e.g. JsonParseStrategy for new sims) are responsible for injecting
        one before calling this function.  The resume path (ReplayParser)
        must continue to return None so that older sims without a traffic
        block stay traffic-free after a resume.
        """
        scenario_content = {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
        }

        config = extract_traffic_config(scenario_content)

        assert config is None

    def test_extract_with_empty_traffic_dict_returns_config_with_default(self) -> None:
        """Test that empty traffic dict returns config with default level."""
        scenario_content = {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
            "traffic": {},
        }

        config = extract_traffic_config(scenario_content)

        assert config is not None
        assert config.traffic_level == "default"

    def test_fallback_to_in_memory_when_no_traffic_block(self) -> None:
        """Test backwards compat: create config from CSV data even without
        traffic block."""
        scenario_content = {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
        }
        csv_data = "TYPE,start_time,segment_key,name,duration,weight\n"

        config = extract_traffic_config(scenario_content, traffic_csv_data=csv_data)

        assert config is not None
        assert config.traffic_level == "default"
        assert config.traffic_csv_data == csv_data
        assert config.sim_start_time == "day1:08:00"
        assert config.sim_end_time == "day1:17:00"

    def test_default_start_end_times(self) -> None:
        """Test default start/end times when not specified."""
        scenario_content = {
            "traffic": {"traffic_level": "low_congestion"},
        }

        config = extract_traffic_config(scenario_content)

        assert config is not None
        assert config.sim_start_time == "day1:00:00"
        assert config.sim_end_time == "day1:00:00"

    def test_non_dict_traffic_value_returns_none(self) -> None:
        """Test that non-dict traffic value returns None."""
        scenario_content = {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
            "traffic": "invalid",
        }

        config = extract_traffic_config(scenario_content)

        assert config is None

    def test_extract_accepts_stop_events_test_template(self) -> None:
        """Test that stop_events_test template is accepted."""
        scenario_content = {
            "start_time": "day1:08:00",
            "end_time": "day1:17:00",
            "traffic": {"traffic_level": "stop_events_test"},
        }

        config = extract_traffic_config(scenario_content)

        assert config is not None
        assert isinstance(config, TrafficConfig)
        assert config.traffic_level == "stop_events_test"

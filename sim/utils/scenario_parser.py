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

from sim.entities.input_parameter import InputParameter
from sim.utils.base_parse_strategy import BaseParseStrategy


class ScenarioParser:
    """Parser for scenario JSON using strategy pattern."""

    def __init__(self, strategy: BaseParseStrategy) -> None:
        """Initialize parser with a parsing strategy.

        Args:
            strategy: Parsing strategy to use for scenario interpretation.
        """
        self._strategy = strategy

    def setStrategy(self, strategy: BaseParseStrategy) -> None:
        """Set a new parsing strategy.

        Args:
            strategy: New parsing strategy to use.

        Returns:
            None
        """
        self._strategy = strategy

    def parse(self, scenario_json: dict) -> InputParameter:
        """Parse scenario JSON using the configured strategy.

        Args:
            scenario_json: Dictionary containing scenario configuration.

        Returns:
            InputParameter object with parsed scenario data.
        """
        return self._strategy.parse(scenario_json=scenario_json)

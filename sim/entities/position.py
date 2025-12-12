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


class Position:
    """Geographical position with longitude and latitude coordinates."""

    def __init__(self, position: list[float]) -> None:  # [longitude, latitude]
        self.position = position

    def get_position(self) -> list[float]:
        """Get the position coordinates.

        Returns:
            List of [longitude, latitude].
        """
        return self.position

    def set_position(self, position: list[float]) -> None:
        """Set the position coordinates.

        Args:
            position: List of [longitude, latitude].

        Returns:
            None
        """
        self.position = position

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Position):
            return False
        return (
            other.position[0] == self.position[0]
            and other.position[1] == self.position[1]
        )

    def close_enough(self, other: object) -> bool:
        """Check if this position is within a certain distance of another position.

        Args:
            other: Another position object to compare with.

        Returns:
            True if positions are within 0.001 units, False otherwise.
        """
        if not isinstance(other, Position):
            return False
        return (
            abs(other.position[0] - self.position[0]) < 0.001
            and abs(other.position[1] - self.position[1]) < 0.001
        )

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

from datetime import datetime
from sim.entities.position import Position


class TestPosition:
    def testPositionWithDefaultTimestamp(self) -> None:
        lat = 45.5017
        lon = -73.5673
        position = Position(lat, lon)

        assert position.latitude == lat
        assert position.longitude == lon
        assert position.timestamp is not None
        assert isinstance(position.timestamp, str)

        # check timestamp format
        datetime.fromisoformat(position.timestamp)

    def testPositionWithCustomTimestamp(self) -> None:
        lat = 40.7128
        lon = -74.0060
        customTimestamp = "2025-01-01T12:00:00"
        position = Position(lat, lon, customTimestamp)

        assert position.latitude == lat
        assert position.longitude == lon
        assert position.timestamp == customTimestamp

    def testGetPosition(self) -> None:
        lat = 45.5017
        lon = -73.5673
        position = Position(lat, lon)

        result = position.getPosition()
        assert result == (lat, lon)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def testSetPosition(self) -> None:
        position = Position(0.0, 0.0)
        newLat = 40.7128
        newLon = -74.0060

        oldTimestamp = position.timestamp
        position.setPosition(newLat, newLon)

        assert position.latitude == newLat
        assert position.longitude == newLon
        assert position.timestamp != oldTimestamp  # timestamp should be updated

    def testUpdateTimestampDefault(self) -> None:
        position = Position(0.0, 0.0, "2020-01-01T00:00:00")
        oldTimestamp = position.timestamp

        position.updateTimestamp()

        assert position.timestamp != oldTimestamp
        datetime.fromisoformat(position.timestamp)

    def testUpdateTimestampCustom(self) -> None:
        position = Position(0.0, 0.0)
        customTimestamp = "2025-12-25T18:00:00"

        position.updateTimestamp(customTimestamp)

        assert position.timestamp == customTimestamp

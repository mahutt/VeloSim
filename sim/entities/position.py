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

class Position:
    def __init__(self, latitude: float, longitude: float, timestamp: str | None = None):
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = timestamp if timestamp is not None else datetime.now().isoformat()

    def getPosition(self):
        return (self.latitude, self.longitude)

    def setPosition(self, latitude: float, longitude: float, timestamp: str | None = None):
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = timestamp if timestamp is not None else datetime.now().isoformat()

    def updateTimestamp(self, timestamp: str | None = None):
        self.timestamp = timestamp if timestamp is not None else datetime.now().isoformat()

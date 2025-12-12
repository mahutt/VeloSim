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

from abc import ABC, abstractmethod
from sim.entities.frame import Frame
from sim.utils.subscriber import Subscriber


class Publisher(ABC):
    """Abstract base class for publisher in observer pattern."""

    @abstractmethod
    def attach(self, sub: Subscriber) -> None:
        """Attach a subscriber to receive frame notifications.

        Args:
            sub: Subscriber instance to attach.

        Returns:
            None
        """
        raise NotImplementedError()

    @abstractmethod
    def detach(self, sub: Subscriber) -> None:
        """Detach a subscriber from receiving frame notifications.

        Args:
            sub: Subscriber instance to detach.

        Returns:
            None
        """
        raise NotImplementedError()

    @abstractmethod
    def notify(self, frame: Frame) -> None:
        """Notify all attached subscribers with a new frame.

        Args:
            frame: Frame data to send to subscribers.

        Returns:
            None
        """
        raise NotImplementedError()

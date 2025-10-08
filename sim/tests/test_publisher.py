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

from sim.entities.frame import Frame
from sim.utils.publisher import Publisher
from sim.utils.subscriber import Subscriber


class FakeSubscriber(Subscriber):
    def __init__(self) -> None:
        self.received: list[Frame] = []

    def on_frame(self, frame: Frame) -> None:
        self.received.append(frame)


def test_publisher_contract_enforced() -> None:
    """
    If Publisher is a proper ABC, instantiation should raise TypeError.
    If not, calling any abstract method should raise NotImplementedError.
    This test passes in both designs.
    """
    try:
        pub = Publisher()  # type: ignore[abstract]
    except TypeError:
        # Class is abstract (inherits from ABC) — good enough.
        return

    # Otherwise, ensure the abstract methods raise at runtime.
    with pytest.raises(NotImplementedError):
        pub.attach(FakeSubscriber())
    with pytest.raises(NotImplementedError):
        pub.detach(FakeSubscriber())
    with pytest.raises(NotImplementedError):
        pub.notify(Frame(seq_number := 1, payload_str="x"))
        _ = seq_number


class ConcretePublisher(Publisher):
    def __init__(self) -> None:
        self._subs: list[Subscriber] = []

    def attach(self, sub: Subscriber) -> None:
        if sub not in self._subs:
            self._subs.append(sub)

    def detach(self, sub: Subscriber) -> None:
        if sub in self._subs:
            self._subs.remove(sub)

    def notify(self, frame: Frame) -> None:
        for s in list(self._subs):
            s.on_frame(frame)


def test_concrete_publisher_attach_detach_notify() -> None:
    pub = ConcretePublisher()
    s1, s2 = FakeSubscriber(), FakeSubscriber()

    pub.attach(s1)
    pub.attach(s2)
    pub.attach(s1)  # idempotent

    f1 = Frame(seq_numb=1, payload_str="hello")
    pub.notify(f1)

    assert [f.seq_number for f in s1.received] == [1]
    assert [f.seq_number for f in s2.received] == [1]

    pub.detach(s1)
    f2 = Frame(seq_numb=2, payload_str="world")
    pub.notify(f2)

    assert [f.seq_number for f in s1.received] == [1]
    assert [f.seq_number for f in s2.received] == [1, 2]

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

import threading
from typing import List

from sim.entities.frame import Frame
from sim.utils.subscriber import Subscriber
from sim.frame_emitter import FrameEmitter


class FakeSubscriber(Subscriber):
    def __init__(self) -> None:
        self.received: List[Frame] = []

    def on_frame(self, frame: Frame) -> None:
        self.received.append(frame)


def test_attach_and_notify_reaches_all_subscribers() -> None:
    emitter = FrameEmitter("sim-123")
    s1, s2 = FakeSubscriber(), FakeSubscriber()

    emitter.attach(s1)
    emitter.attach(s2)

    frame = Frame(seq_numb=1, payload="hello")
    emitter.notify(frame)

    assert s1.received == [frame]
    assert s2.received == [frame]


def test_attach_is_idempotent_no_duplicates() -> None:
    emitter = FrameEmitter("sim-123")
    s = FakeSubscriber()

    emitter.attach(s)
    emitter.attach(s)

    frame = Frame(seq_numb=2, payload="world")
    emitter.notify(frame)

    assert s.received == [frame]


def test_detach_stops_delivery() -> None:
    emitter = FrameEmitter("sim-123")
    s = FakeSubscriber()

    emitter.attach(s)
    emitter.notify(Frame(seq_numb=3, payload="before"))
    emitter.detach(s)
    emitter.notify(Frame(seq_numb=4, payload="after"))

    assert [f.seq_number for f in s.received] == [3]


def test_notify_is_thread_safe() -> None:
    emitter = FrameEmitter("sim-123")
    subs = [FakeSubscriber() for _ in range(10)]
    for s in subs[:5]:
        emitter.attach(s)

    stop = threading.Event()

    def churn() -> None:
        i = 0
        while not stop.is_set():
            s = subs[i % len(subs)]
            emitter.attach(s)
            emitter.detach(s)
            i += 1

    t = threading.Thread(target=churn, daemon=True)
    t.start()

    for n in range(10):
        emitter.notify(Frame(seq_numb=n, payload=f"frame {n}"))

    stop.set()
    t.join(timeout=1.0)

    assert any(s.received for s in subs)

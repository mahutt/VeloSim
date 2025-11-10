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
from sim.core.frame_emitter import FrameEmitter


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

    frame = Frame(seq_numb=1, payload_str="hello")
    emitter.notify(frame)

    assert s1.received == [frame]
    assert s2.received == [frame]


def test_attach_is_idempotent_no_duplicates() -> None:
    emitter = FrameEmitter("sim-123")
    s = FakeSubscriber()

    emitter.attach(s)
    emitter.attach(s)

    frame = Frame(seq_numb=2, payload_str="world")
    emitter.notify(frame)

    assert s.received == [frame]


def test_detach_stops_delivery() -> None:
    emitter = FrameEmitter("sim-123")
    s = FakeSubscriber()

    emitter.attach(s)
    emitter.notify(Frame(seq_numb=3, payload_str="before"))
    emitter.detach(s)
    emitter.notify(Frame(seq_numb=4, payload_str="after"))

    assert [f.seq_number for f in s.received] == [3]


def test_notify_is_thread_safe() -> None:
    emitter = FrameEmitter("sim-123")
    subs = [FakeSubscriber() for _ in range(10)]

    # Keep some subscribers permanently attached to ensure they receive notifications
    for s in subs[:3]:
        emitter.attach(s)

    stop = threading.Event()

    def churn() -> None:
        i = 0
        while not stop.is_set():
            # Only churn the last 7 subscribers, leaving the first 3 always attached
            s = subs[3 + (i % 7)]
            emitter.attach(s)
            emitter.detach(s)
            i += 1
            # Add occasional pauses to prevent overwhelming the system
            if i % 50 == 0:
                threading.Event().wait(0.001)

    t = threading.Thread(target=churn, daemon=True)
    t.start()

    # Send notifications with small delays
    for n in range(10):
        emitter.notify(Frame(seq_numb=n, payload_str=f"frame {n}"))
        threading.Event().wait(0.001)

    stop.set()
    t.join(timeout=1.0)

    # At least the permanently attached subscribers should have received something
    assert any(
        s.received for s in subs[:3]
    ), "Permanently attached subscribers should receive notifications"

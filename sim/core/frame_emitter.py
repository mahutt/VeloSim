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
from sim.utils.publisher import Publisher
from sim.utils.subscriber import Subscriber


class FrameEmitter(Publisher):
    def __init__(self, sim_id: str) -> None:
        self.subscribers: List[Subscriber] = []
        self.sim_id = sim_id
        self._lock = threading.Lock()

    def attach(self, sub: Subscriber) -> None:
        with self._lock:
            if sub not in self.subscribers:
                self.subscribers.append(sub)

    def detach(self, sub: Subscriber) -> None:
        with self._lock:
            if sub in self.subscribers:
                self.subscribers.remove(sub)

    def notify(self, frame: Frame) -> None:
        with self._lock:
            live_subscribers = list(
                self.subscribers
            )  # Taking live subs to prevent deadlock.

        for subs in live_subscribers:
            subs.on_frame(frame)

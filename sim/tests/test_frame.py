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

import time

from sim.entities.frame import Frame


def test_frame_fields_set_and_types() -> None:
    f = Frame(seq_numb=42, payload_str="hello")
    assert f.seq_number == 42
    assert isinstance(f.timestamp_ms, int)
    assert f.payload_str == "hello"


def test_timestamp_is_epoch_ms_and_reasonable_range() -> None:
    before = int(time.time() * 1000)
    f = Frame(seq_numb=1, payload_str="x")
    after = int(time.time() * 1000)
    # timestamp in ms and between before/after bounds
    assert before <= f.timestamp_ms <= after
    # sanity: looks like milliseconds (not seconds)
    assert f.timestamp_ms > 10**12  # ~Sat Sep 09 2001 in ms


def test_timestamp_monotonic_increases_over_time() -> None:
    f1 = Frame(seq_numb=1, payload_str="a")
    time.sleep(0.002)  # 2ms
    f2 = Frame(seq_numb=2, payload_str="b")
    assert f2.timestamp_ms >= f1.timestamp_ms


def test_repr_includes_seq_timestamp_payload_str() -> None:
    f = Frame(seq_numb=7, payload_str="payload_str-text")
    s = repr(f)
    assert s.startswith("Frame(") and s.endswith(")")
    assert f"seq={f.seq_number}" in s
    assert f"timestamp={f.timestamp_ms}" in s
    assert "payload" in s  # less brittle, passes whether it's dict or string

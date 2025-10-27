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

import json
import time
from typing import Any, Dict, Optional


class Frame:
    def __init__(
        self,
        seq_numb: int,
        payload: Optional[Dict[str, Any]] = None,
        payload_str: Optional[str] = None,
        is_key: Optional[bool] = False,
    ) -> None:
        self.seq_number = seq_numb
        self.timestamp_ms = int(time.time() * 1000)
        self.payload_dict = payload or {}
        self.is_key = is_key

        if payload_str:
            self.payload_str = payload_str
        elif payload:
            self.payload_str = json.dumps(payload)
        else:
            self.payload_str = "{}"

    def __repr__(self) -> str:
        return (
            f"Frame(seq={self.seq_number}, "
            f"timestamp={self.timestamp_ms}, "
            f"payload={self.payload_dict}, "
            f"is_key={self.is_key})"
        )

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

# Include all utilities here for easy access
from .sim_websocket_helpers import (
    WebSocketSubscriber,
    safe_send_json,
    get_simulation_or_error,
    attach_ws_subscriber,
    start_or_resume_simulation,
    cleanup_simulation,
    accept_websocket_connection,
    verify_simulation_access,
    run_message_loop,
)

__all__ = [
    "WebSocketSubscriber",
    "safe_send_json",
    "get_simulation_or_error",
    "attach_ws_subscriber",
    "start_or_resume_simulation",
    "cleanup_simulation",
    "accept_websocket_connection",
    "verify_simulation_access",
    "run_message_loop",
]

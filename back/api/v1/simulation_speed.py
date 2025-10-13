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

from fastapi import APIRouter
from back.schemas.playback_speed import PlaybackSpeedBase, PlaybackSpeedResponse
from back.crud.simulation_speed import playback_speed_crud

router = APIRouter(prefix="/playback_speed", tags=["Playback Speed"])


@router.post("/", response_model=PlaybackSpeedResponse)
async def set_playback_speed(task: PlaybackSpeedBase) -> PlaybackSpeedResponse:
    """Set or update the playback speed for a simulation."""
    return playback_speed_crud.update(task.simulation_id, task.playback_speed)


@router.get("/{simulation_id}", response_model=PlaybackSpeedResponse)
async def get_playback_speed(simulation_id: int) -> PlaybackSpeedResponse:
    """Get the current playback speed for a given simulation."""
    return playback_speed_crud.get(simulation_id)


@router.get("/", response_model=list[PlaybackSpeedResponse])
def get_all_playback_speeds() -> list[PlaybackSpeedResponse]:
    return playback_speed_crud.get_all()

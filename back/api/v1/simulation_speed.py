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

from fastapi import APIRouter, HTTPException
from back.schemas.playback_speed import PlaybackSpeedBase, PlaybackSpeedResponse

router = APIRouter(prefix="/playback", tags=["Playback Speed"])


playback_store: dict[int, float] = {}


@router.post("/", response_model=PlaybackSpeedResponse)
async def set_playback_speed(task: PlaybackSpeedBase) -> PlaybackSpeedResponse:
    """
    Set the playback speed for a simulation.
    """
    if task.playback_speed <= 0:
        raise HTTPException(status_code=400, detail="Playback speed must be positive.")
    elif task.playback_speed > 12:
        raise HTTPException(
            status_code=400, detail="Playback speed value is too large."
        )
    playback_store[task.simulation_id] = task.playback_speed

    return PlaybackSpeedResponse(
        simulation_id=task.simulation_id,
        playback_speed=task.playback_speed,
        message="Playback speed updated successfully.",
    )


@router.get("/{simulation_id}", response_model=PlaybackSpeedResponse)
async def get_playback_speed(simulation_id: int) -> PlaybackSpeedResponse:
    """
    Get the current playback speed for a simulation.
    """
    speed = playback_store.get(simulation_id)
    if speed is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    return PlaybackSpeedResponse(
        simulation_id=simulation_id,
        playback_speed=speed,
        message="Playback speed retrieved successfully.",
    )

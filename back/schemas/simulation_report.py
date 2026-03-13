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

from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class SimulationReportResponse(BaseModel):
    """Response schema for simulation reporting metrics.

    All fields default to None so clients can distinguish missing metrics
    from measured zero values.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    servicing_to_driving_ratio: float | None = Field(
        None, description="Servicing to driving ratio"
    )
    vehicle_utilization_ratio: float | None = Field(
        None, description="Vehicle utilization ratio"
    )
    average_tasks_serviced_per_shift: float | None = Field(
        None, description="Average tasks serviced per shift"
    )
    average_task_response_time: float | None = Field(
        None, description="Average task response time"
    )
    vehicle_distance_traveled: float | None = Field(
        None, description="Vehicle Distance Traveled"
    )

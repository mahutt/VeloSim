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

from back.database.session import SessionLocal
from back.crud.sim_instance import sim_instance_crud
from grafana_logging.logger import get_logger
from back.core.simulation_lag_monitor import simulation_lag_histogram

logger = get_logger(__name__)


def on_simulation_completed(sim_id: str) -> None:
    """Mark a simulation as completed in the database.

    Args:
        sim_id (str): UUID of the completed simulation.

    Returns:
        None
    """

    try:
        with SessionLocal() as db:
            sim_instance = sim_instance_crud.get_by_uuid(db, sim_id)

            if not sim_instance:
                logger.warning(
                    "Simulation completion callback: no simulation found (uuid=%s)",
                    sim_id,
                )
                return
            sim_instance.completed = True
            db.commit()

            logger.info(
                "Simulation marked as completed (uuid=%s, id=%s)",
                sim_id,
                sim_instance.id,
            )
    except Exception:
        logger.exception(
            "Simulation completion callback failed (uuid=%s)",
            sim_id,
        )


def report_simulation_lag(lag: float) -> None:
    """
    Used to report simulation lag

    Args:
        lag: seconds for which the simulation is lagging

    Returns:
        None
    """
    simulation_lag_histogram.record(lag)

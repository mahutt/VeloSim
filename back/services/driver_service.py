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

from back.exceptions.item_not_found_error import ItemNotFoundError
from back.exceptions.velosim_permission_error import VelosimPermissionError
from back.services.simulation_service import simulation_service

from back.schemas import (
    DriverTaskAssignRequest,
    DriverTaskAssignResponse,
    DriverTaskReassignRequest,
    DriverTaskReassignResponse,
    DriverTaskUnassignRequest,
    DriverTaskUnassignResponse,
    DriverTaskReorderRequest,
    DriverTaskReorderResponse,
)
from sqlalchemy.orm import Session


class DriverService:
    """Operations for managing drivers within a simulation instance."""

    def assign_task(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        task_assign_data: DriverTaskAssignRequest,
    ) -> DriverTaskAssignResponse:
        """
        Assign a task to a driver in a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            task_assign_data: Data containing the task ID to assign

        Returns:
            DriverTaskAssignResponse: Confirmation that the task was assigned.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the task or driver does not exist in the simulation.
            RuntimeError: If assigning the task fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = simulation_service.simulator
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        try:
            # Assign task to driver in the running sim
            simulator.assign_task_to_driver(
                sim_id=sim_id,
                task_id=task_assign_data.task_id,
                driver_id=task_assign_data.driver_id,
            )
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if "Could not find task" in msg:
                raise ItemNotFoundError(
                    f"Task {task_assign_data.task_id} not found"
                ) from err
            elif "Could not find driver" in msg:
                raise ItemNotFoundError(
                    f"Driver {task_assign_data.driver_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message upon successful assignment
        return DriverTaskAssignResponse(
            driver_id=task_assign_data.driver_id,
            task_id=task_assign_data.task_id,
        )

    def unassign_task(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        task_unassign_data: DriverTaskUnassignRequest,
    ) -> DriverTaskUnassignResponse:
        """
        Unassign a task from a driver in a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            task_unassign_data: Data containing the task ID to unassign

        Returns:
            DriverTaskUnassignResponse: Confirmation that the task was unassigned.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the task or driver does not exist in the simulation.
            RuntimeError: If assigning the task fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = simulation_service.simulator
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        try:
            simulator.unassign_task_from_driver(
                sim_id=sim_id,
                task_id=task_unassign_data.task_id,
                driver_id=task_unassign_data.driver_id,
            )
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if "Could not find task" in msg:
                raise ItemNotFoundError(
                    f"Task {task_unassign_data.task_id} not found"
                ) from err
            elif "Could not find driver" in msg:
                raise ItemNotFoundError(
                    f"Driver {task_unassign_data.driver_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message upon successful unassignment
        return DriverTaskUnassignResponse(
            driver_id=task_unassign_data.driver_id,
            task_id=task_unassign_data.task_id,
        )

    def reassign_task(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        task_reassign_data: DriverTaskReassignRequest,
    ) -> DriverTaskReassignResponse:
        """
        Reassign a task from one driver to another in a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            task_reassign_data: Data containing the task ID to reassign

        Returns:
            DriverTaskReassignResponse: Confirmation that the task was reassigned.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the task or driver does not exist in the simulation.
            RuntimeError: If assigning the task fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = simulation_service.simulator
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        try:
            simulator.reassign_task(
                sim_id=sim_id,
                task_id=task_reassign_data.task_id,
                old_driver_id=task_reassign_data.old_driver_id,
                new_driver_id=task_reassign_data.new_driver_id,
            )
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if str(task_reassign_data.task_id) in msg:
                raise ItemNotFoundError(
                    f"Task {task_reassign_data.task_id} not found"
                ) from err
            elif str(task_reassign_data.old_driver_id) in msg:
                raise ItemNotFoundError(
                    f"Old driver {task_reassign_data.old_driver_id} not found"
                ) from err
            elif str(task_reassign_data.new_driver_id) in msg:
                raise ItemNotFoundError(
                    f"New driver {task_reassign_data.new_driver_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message upon successful reassignment
        return DriverTaskReassignResponse(
            task_id=task_reassign_data.task_id,
            old_driver_id=task_reassign_data.old_driver_id,
            new_driver_id=task_reassign_data.new_driver_id,
        )

    def reorder_tasks(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        reorder_data: DriverTaskReorderRequest,
    ) -> DriverTaskReorderResponse:
        """
        Reorder tasks in a driver's task list within a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            reorder_data: Data containing driver ID, task IDs, and reorder mode

        Returns:
            DriverTaskReorderResponse: Confirmation with complete new task order.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the driver does not exist in the simulation.
            RuntimeError: If reordering fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = simulation_service.simulator
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        try:
            new_task_order = simulator.reorder_driver_tasks(
                sim_id=sim_id,
                driver_id=reorder_data.driver_id,
                task_ids_to_reorder=reorder_data.task_ids,
                apply_from_top=reorder_data.apply_from_top,
            )
        except ValueError as err:
            # Validation errors (empty list, duplicates)
            raise RuntimeError(f"Invalid reorder request: {err}") from err
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if "Could not find driver" in msg:
                raise ItemNotFoundError(
                    f"Driver {reorder_data.driver_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message with the new task order
        return DriverTaskReorderResponse(
            driver_id=reorder_data.driver_id,
            task_order=new_task_order,
        )


# Global singleton
driver_service = DriverService()

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
from grafana_logging.logger import get_logger

from back.schemas import (
    DriverTaskAssignRequest,
    DriverTaskAssignResponse,
    DriverTaskReassignRequest,
    DriverTaskReassignResponse,
    DriverTaskUnassignRequest,
    DriverTaskUnassignResponse,
    DriverTaskReorderRequest,
    DriverTaskReorderResponse,
    DriverTaskBatchAssignResponse,
    DriverTaskBatchAssignItem,
    DriverTaskBatchAssignRequest,
    DriverTaskBatchUnassignRequest,
    DriverTaskBatchUnassignResponse,
    DriverTaskBatchUnassignItem,
)
from sqlalchemy.orm import Session

logger = get_logger(__name__)


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

        logger.info(
            "Task assigned: sim_id=%s, driver_id=%s, task_id=%s, user_id=%s",
            sim_id,
            task_assign_data.driver_id,
            task_assign_data.task_id,
            requesting_user,
        )
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

        This operation is strict (non-idempotent): it fails when the task is
        already unassigned, assigned to a different driver, or currently in
        service and therefore not unassignable.

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

        logger.info(
            "Task unassigned: sim_id=%s, driver_id=%s, task_id=%s, user_id=%s",
            sim_id,
            task_unassign_data.driver_id,
            task_unassign_data.task_id,
            requesting_user,
        )
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

        logger.info(
            "Task reassigned: sim_id=%s, task_id=%s, "
            "old_driver_id=%s, new_driver_id=%s, user_id=%s",
            sim_id,
            task_reassign_data.task_id,
            task_reassign_data.old_driver_id,
            task_reassign_data.new_driver_id,
            requesting_user,
        )
        # Return a confirmation message upon successful reassignment
        return DriverTaskReassignResponse(
            task_id=task_reassign_data.task_id,
            old_driver_id=task_reassign_data.old_driver_id,
            new_driver_id=task_reassign_data.new_driver_id,
        )

    def batch_assign(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        batch_request: DriverTaskBatchAssignRequest,
    ) -> DriverTaskBatchAssignResponse:
        """Batch assign or reassign tasks to a driver within a running simulation.

        For each task in the request:
        - If unassigned: assigns to the target driver
        - If already assigned to target driver: treats as success (no-op)
        - If assigned to a different driver: reassigns to the target driver

        Note:
            This method performs best-effort operations: each item is
            attempted independently and the response contains per-item
            success/failure details. No rollback is performed.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            batch_request: Request containing `driver_id` and `task_ids` to apply

        Returns:
            DriverTaskBatchAssignResponse: Per-item assignment results.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the simulation is not found.
            RuntimeError: If simulator batch call fails entirely.
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

        items: list[DriverTaskBatchAssignItem] = []

        # Use simulator batch API for efficiency; service accepts a single
        # DriverTaskBatchAssignRequest containing a `driver_id` and a
        # list of `task_ids`.
        if not batch_request or not batch_request.task_ids:
            return DriverTaskBatchAssignResponse(items=[])

        driver_id = batch_request.driver_id
        task_ids = list(batch_request.task_ids)

        try:
            batch_results = simulator.batch_assign_tasks_to_driver(
                sim_id=sim_id, driver_id=driver_id, task_ids=task_ids
            )
        except Exception as err:
            # If simulator-level call fails entirely, propagate as runtime error
            raise RuntimeError(f"Simulator batch assign failed: {err}") from err

        # Convert simulator results to schema items. Validate presence
        # of required fields before casting to avoid passing None to int().
        for r in batch_results:
            drv_val = r.get("driver_id")
            tsk_val = r.get("task_id")
            if drv_val is None or tsk_val is None:
                raise RuntimeError("Simulator returned malformed batch item")
            driver_id_int = int(drv_val)
            task_id_int = int(tsk_val)
            success_bool = bool(r.get("success"))
            err_val = r.get("error")
            items.append(
                DriverTaskBatchAssignItem(
                    driver_id=driver_id_int,
                    task_id=task_id_int,
                    success=success_bool,
                    error=(err_val if err_val is not None else None),
                )
            )

        logger.info(
            "Batch assign: sim_id=%s, driver_id=%s, task_ids=%s, user_id=%s",
            sim_id,
            driver_id,
            task_ids,
            requesting_user,
        )
        return DriverTaskBatchAssignResponse(items=items)

    def batch_unassign(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        batch_request: DriverTaskBatchUnassignRequest,
    ) -> DriverTaskBatchUnassignResponse:
        """Batch unassign many tasks from their currently assigned drivers.

        For each task in the request:
        - If task is already unassigned: returns success (no-op)
        - Resolves current assigned driver from simulator state
        - Unassigns task from that driver

        Each unassignment is attempted independently and the response contains
        per-item success/failure details. No rollback is performed.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            batch_request: Request containing `task_ids` to unassign

        Returns:
            DriverTaskBatchUnassignResponse: Per-item unassignment results.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the simulation is not found.
            RuntimeError: If simulator-level setup for batch unassign fails.
        """

        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = simulation_service.simulator
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        items: list[DriverTaskBatchUnassignItem] = []
        task_ids = list(batch_request.task_ids)

        try:
            batch_results = simulator.batch_unassign_tasks_from_drivers(
                sim_id=sim_id,
                task_ids=task_ids,
            )
        except Exception as err:
            raise RuntimeError(f"Simulator batch unassign failed: {err}") from err

        for r in batch_results:
            tsk_val = r.get("task_id")
            if tsk_val is None:
                raise RuntimeError("Simulator returned malformed batch unassign item")
            task_id_int = int(tsk_val)

            drv_val = r.get("driver_id")
            driver_id_int = int(drv_val) if drv_val is not None else None

            success_bool = bool(r.get("success"))
            err_val = r.get("error")

            items.append(
                DriverTaskBatchUnassignItem(
                    task_id=task_id_int,
                    driver_id=driver_id_int,
                    success=success_bool,
                    error=(err_val if err_val is not None else None),
                )
            )

        logger.info(
            "Batch unassign: sim_id=%s, task_ids=%s, user_id=%s",
            sim_id,
            task_ids,
            requesting_user,
        )
        return DriverTaskBatchUnassignResponse(items=items)

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

        logger.info(
            "Tasks reordered: sim_id=%s, driver_id=%s, task_ids=%s, user_id=%s",
            sim_id,
            reorder_data.driver_id,
            reorder_data.task_ids,
            requesting_user,
        )
        # Return a confirmation message with the new task order
        return DriverTaskReorderResponse(
            driver_id=reorder_data.driver_id,
            task_order=new_task_order,
        )


# Global singleton
driver_service = DriverService()

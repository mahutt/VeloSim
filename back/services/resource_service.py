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

# Database persistence currently disabled
# from back.crud.resource import resource_crud
from back.schemas import (
    ResourceTaskAssignRequest,
    ResourceTaskAssignResponse,
    ResourceTaskReassignRequest,
    ResourceTaskReassignResponse,
    ResourceTaskUnassignRequest,
    ResourceTaskUnassignResponse,
    ResourceTaskReorderRequest,
    ResourceTaskReorderResponse,
)
from sqlalchemy.orm import Session


class ResourceService:
    """Operations for managing resources within a simulation instance."""

    # The following service-level, sim-scoped resource operations are currently
    # disabled because unification between the in-memory entities and database
    # records is not yet available:
    # create_resource
    # get_resource
    # get_resources
    # update_resource
    # delete_resource
    # The methods below operate only on the runtime sim (in-memory) state.
    # They do not persist changes to the database.

    def assign_task(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        task_assign_data: ResourceTaskAssignRequest,
    ) -> ResourceTaskAssignResponse:
        """
        Assign a task to a resource in a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            task_assign_data: Data containing the task ID to assign

        Returns:
            ResourceTaskAssignResponse: Confirmation that the task was assigned.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the task or resource does not exist in the simulation.
            RuntimeError: If assigning the task fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = sim_data.get("simulator")
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        try:
            # Assign task to resource in the running sim
            simulator.assign_task_to_resource(
                sim_id=sim_id,
                task_id=task_assign_data.task_id,
                resource_id=task_assign_data.resource_id,
            )
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if "Could not find task" in msg:
                raise ItemNotFoundError(
                    f"Task {task_assign_data.task_id} not found"
                ) from err
            elif "Could not find resource" in msg:
                raise ItemNotFoundError(
                    f"Resource {task_assign_data.resource_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message upon successful assignment
        return ResourceTaskAssignResponse(
            resource_id=task_assign_data.resource_id,
            task_id=task_assign_data.task_id,
        )

    def unassign_task(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        task_unassign_data: ResourceTaskUnassignRequest,
    ) -> ResourceTaskUnassignResponse:
        """
        Unassign a task from a resource in a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            task_unassign_data: Data containing the task ID to unassign

        Returns:
            ResourceTaskUnassignResponse: Confirmation that the task was unassigned.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the task or resource does not exist in the simulation.
            RuntimeError: If assigning the task fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = sim_data.get("simulator")
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        try:
            simulator.unassign_task_from_resource(
                sim_id=sim_id,
                task_id=task_unassign_data.task_id,
                resource_id=task_unassign_data.resource_id,
            )
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if "Could not find task" in msg:
                raise ItemNotFoundError(
                    f"Task {task_unassign_data.task_id} not found"
                ) from err
            elif "Could not find resource" in msg:
                raise ItemNotFoundError(
                    f"Resource {task_unassign_data.resource_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message upon successful unassignment
        return ResourceTaskUnassignResponse(
            resource_id=task_unassign_data.resource_id,
            task_id=task_unassign_data.task_id,
        )

    def reassign_task(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        task_reassign_data: ResourceTaskReassignRequest,
    ) -> ResourceTaskReassignResponse:
        """
        Reassign a task from one resource to another in a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            task_reassign_data: Data containing the task ID to reassign

        Returns:
            ResourceTaskReassignResponse: Confirmation that the task was reassigned.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the task or resource does not exist in the simulation.
            RuntimeError: If assigning the task fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = sim_data.get("simulator")
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        try:
            simulator.reassign_task(
                sim_id=sim_id,
                task_id=task_reassign_data.task_id,
                old_resource_id=task_reassign_data.old_resource_id,
                new_resource_id=task_reassign_data.new_resource_id,
            )
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if str(task_reassign_data.task_id) in msg:
                raise ItemNotFoundError(
                    f"Task {task_reassign_data.task_id} not found"
                ) from err
            elif str(task_reassign_data.old_resource_id) in msg:
                raise ItemNotFoundError(
                    f"Old resource {task_reassign_data.old_resource_id} not found"
                ) from err
            elif str(task_reassign_data.new_resource_id) in msg:
                raise ItemNotFoundError(
                    f"New resource {task_reassign_data.new_resource_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message upon successful reassignment
        return ResourceTaskReassignResponse(
            task_id=task_reassign_data.task_id,
            old_resource_id=task_reassign_data.old_resource_id,
            new_resource_id=task_reassign_data.new_resource_id,
        )

    def reorder_tasks(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
        reorder_data: ResourceTaskReorderRequest,
    ) -> ResourceTaskReorderResponse:
        """
        Reorder tasks in a resource's task list within a running simulation instance.

        Note:
            This method operates on runtime simulation objects (in-memory IDs).
            The `requesting_user` parameter refers to a database user ID.

        Args:
            db: Database session
            sim_id: UUID of the active in-memory simulation
            requesting_user: Database ID of the user performing the action
            reorder_data: Data containing resource ID, task IDs, and reorder mode

        Returns:
            ResourceTaskReorderResponse: Confirmation with complete new task order.

        Raises:
            VelosimPermissionError: If the user cannot access this simulation.
            ItemNotFoundError: If the resource does not exist in the simulation.
            RuntimeError: If reordering fails for any other reason.
        """

        # Verify that the requesting user has permission to access the sim
        if not simulation_service.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to access this simulation")

        # Get the simulator manager that tracks all active simulations
        sim_data = simulation_service.active_simulations.get(sim_id)
        if not sim_data:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        simulator = sim_data.get("simulator")
        if simulator is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        try:
            new_task_order = simulator.reorder_resource_tasks(
                sim_id=sim_id,
                resource_id=reorder_data.resource_id,
                task_ids_to_reorder=reorder_data.task_ids,
                apply_from_top=reorder_data.apply_from_top,
            )
        except ValueError as err:
            # Validation errors (empty list, duplicates)
            raise RuntimeError(f"Invalid reorder request: {err}") from err
        except Exception as err:
            # Inspect the error message to return a specific Error
            msg = str(err)
            if "Could not find resource" in msg:
                raise ItemNotFoundError(
                    f"Resource {reorder_data.resource_id} not found"
                ) from err
            else:
                # The error is internal
                raise RuntimeError(f"Failed operation: {err}") from err

        # Return a confirmation message with the new task order
        return ResourceTaskReorderResponse(
            resource_id=reorder_data.resource_id,
            task_order=new_task_order,
        )


# Global singleton
resource_service = ResourceService()

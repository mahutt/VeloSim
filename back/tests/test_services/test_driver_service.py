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

from typing import Any, Dict, Generator
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from back.services.driver_service import driver_service
from back.services.simulation_service import simulation_service
from back.schemas import (
    DriverTaskAssignRequest,
    DriverTaskAssignResponse,
    DriverTaskUnassignRequest,
    DriverTaskUnassignResponse,
    DriverTaskReassignRequest,
    DriverTaskReassignResponse,
    DriverTaskReorderRequest,
    DriverTaskReorderResponse,
    DriverTaskBatchAssignResponse,
    DriverTaskBatchAssignRequest,
    DriverTaskBatchUnassignRequest,
    DriverTaskBatchUnassignResponse,
)
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from sim.simulator import Simulator


@pytest.fixture
def db_session() -> Session:
    """Mocked database session."""
    return Mock(spec=Session)


@pytest.fixture
def sim_id() -> str:
    return "fake-sim-id"


@pytest.fixture
def requesting_user() -> int:
    return 42


@pytest.fixture
def simulator_mock() -> Mock:
    """Mocked simulator instance."""
    return Mock(spec=Simulator)


@pytest.fixture(autouse=True)
def patch_active_simulations(
    simulator_mock: Mock, sim_id: str
) -> Generator[Dict[str, Any], None, None]:
    """Patch simulation_service.active_simulations and verify_access."""
    fake_active_sim = {sim_id: {"simulator": simulator_mock}}
    with (
        patch.object(simulation_service, "active_simulations", fake_active_sim),
        patch.object(simulation_service, "simulator", simulator_mock),
        patch.object(
            simulation_service, "verify_access", return_value=True
        ) as mock_verify,
    ):
        yield {"verify_access": mock_verify, "simulator": simulator_mock}


class TestDriverService:
    """Tests for DriverService using updated active_simulations."""

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    def test_assign_task_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Test successful task assignment.

        Note: Warnings suppressed because mocking the simulator can trigger
        unawaited coroutines in FramePersistenceSubscriber._persistence_worker,
        and event loop cleanup from other tests can cause unraisable exceptions.
        """
        payload = DriverTaskAssignRequest(driver_id=1, task_id=100)
        response = driver_service.assign_task(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations[
            "simulator"
        ].assign_task_to_driver.assert_called_once_with(
            sim_id=sim_id, task_id=100, driver_id=1
        )
        assert isinstance(response, DriverTaskAssignResponse)
        assert response.task_id == 100
        assert response.driver_id == 1

    def test_assign_task_permission_denied(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
    ) -> None:
        payload = DriverTaskAssignRequest(driver_id=1, task_id=100)
        with patch.object(simulation_service, "verify_access", return_value=False):
            with pytest.raises(VelosimPermissionError):
                driver_service.assign_task(db_session, sim_id, requesting_user, payload)

    def test_assign_task_not_found(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        patch_active_simulations["simulator"].assign_task_to_driver.side_effect = (
            Exception("Could not find task")
        )
        payload = DriverTaskAssignRequest(driver_id=1, task_id=100)
        with pytest.raises(ItemNotFoundError, match="Task 100 not found"):
            driver_service.assign_task(db_session, sim_id, requesting_user, payload)

    def test_assign_task_runtime_error(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        patch_active_simulations["simulator"].assign_task_to_driver.side_effect = (
            Exception("Unexpected failure")
        )
        payload = DriverTaskAssignRequest(driver_id=1, task_id=100)
        with pytest.raises(RuntimeError, match="Failed operation: Unexpected failure"):
            driver_service.assign_task(db_session, sim_id, requesting_user, payload)

    def test_unassign_task_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        payload = DriverTaskUnassignRequest(driver_id=1, task_id=100)
        response = driver_service.unassign_task(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations[
            "simulator"
        ].unassign_task_from_driver.assert_called_once_with(
            sim_id=sim_id, task_id=100, driver_id=1
        )
        assert isinstance(response, DriverTaskUnassignResponse)
        assert response.task_id == 100
        assert response.driver_id == 1

    def test_unassign_task_permission_denied(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
    ) -> None:
        payload = DriverTaskUnassignRequest(driver_id=1, task_id=100)
        with patch.object(simulation_service, "verify_access", return_value=False):
            with pytest.raises(VelosimPermissionError):
                driver_service.unassign_task(
                    db_session, sim_id, requesting_user, payload
                )

    @pytest.mark.parametrize(
        "exception_msg,expected_error",
        [
            ("Could not find task", "Task 100 not found"),
            ("Could not find driver", "Driver 1 not found"),
            ("Unexpected failure", "Failed operation: Unexpected failure"),
        ],
    )
    def test_unassign_task_exceptions(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        exception_msg: str,
        expected_error: str,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        patch_active_simulations["simulator"].unassign_task_from_driver.side_effect = (
            Exception(exception_msg)
        )
        payload = DriverTaskUnassignRequest(driver_id=1, task_id=100)
        if "Unexpected" in exception_msg:
            with pytest.raises(RuntimeError, match=expected_error):
                driver_service.unassign_task(
                    db_session, sim_id, requesting_user, payload
                )
        else:
            with pytest.raises(ItemNotFoundError, match=expected_error):
                driver_service.unassign_task(
                    db_session, sim_id, requesting_user, payload
                )

    def test_reassign_task_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        payload = DriverTaskReassignRequest(
            task_id=100, old_driver_id=1, new_driver_id=2
        )
        response = driver_service.reassign_task(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations["simulator"].reassign_task.assert_called_once_with(
            sim_id=sim_id, task_id=100, old_driver_id=1, new_driver_id=2
        )
        assert isinstance(response, DriverTaskReassignResponse)
        assert response.task_id == 100
        assert response.old_driver_id == 1
        assert response.new_driver_id == 2

    @pytest.mark.parametrize(
        "exception_msg,expected_error",
        [
            ("100", "Task 100 not found"),
            ("1", "Old driver 1 not found"),
            ("2", "New driver 2 not found"),
            ("Unexpected failure", "Failed operation: Unexpected failure"),
        ],
    )
    def test_reassign_task_exceptions(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        exception_msg: str,
        expected_error: str,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        patch_active_simulations["simulator"].reassign_task.side_effect = Exception(
            exception_msg
        )
        payload = DriverTaskReassignRequest(
            task_id=100, old_driver_id=1, new_driver_id=2
        )
        if "Unexpected" in exception_msg:
            with pytest.raises(RuntimeError, match=expected_error):
                driver_service.reassign_task(
                    db_session, sim_id, requesting_user, payload
                )
        else:
            with pytest.raises(ItemNotFoundError, match=expected_error):
                driver_service.reassign_task(
                    db_session, sim_id, requesting_user, payload
                )

    def test_reorder_tasks_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Test successful task reordering."""
        patch_active_simulations["simulator"].reorder_driver_tasks.return_value = [
            3,
            1,
            2,
        ]
        payload = DriverTaskReorderRequest(
            driver_id=1, task_ids=[3, 1], apply_from_top=True
        )
        response = driver_service.reorder_tasks(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations[
            "simulator"
        ].reorder_driver_tasks.assert_called_once_with(
            sim_id=sim_id,
            driver_id=1,
            task_ids_to_reorder=[3, 1],
            apply_from_top=True,
        )
        assert isinstance(response, DriverTaskReorderResponse)
        assert response.driver_id == 1
        assert response.task_order == [3, 1, 2]

    def test_reorder_tasks_permission_denied(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
    ) -> None:
        """Test reorder with permission denied."""
        payload = DriverTaskReorderRequest(
            driver_id=1, task_ids=[3, 1], apply_from_top=True
        )
        with patch.object(simulation_service, "verify_access", return_value=False):
            with pytest.raises(VelosimPermissionError):
                driver_service.reorder_tasks(
                    db_session, sim_id, requesting_user, payload
                )

    def test_reorder_tasks_driver_not_found(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Test reorder with driver not found."""
        patch_active_simulations["simulator"].reorder_driver_tasks.side_effect = (
            Exception("Could not find driver")
        )
        payload = DriverTaskReorderRequest(
            driver_id=999, task_ids=[1, 2], apply_from_top=True
        )
        with pytest.raises(ItemNotFoundError, match="Driver 999 not found"):
            driver_service.reorder_tasks(db_session, sim_id, requesting_user, payload)

    def test_reorder_tasks_empty_list_error(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Test reorder with empty task list raises ValueError."""
        patch_active_simulations["simulator"].reorder_driver_tasks.side_effect = (
            ValueError("task_ids_to_reorder cannot be empty")
        )
        payload = DriverTaskReorderRequest(
            driver_id=1, task_ids=[1], apply_from_top=True
        )
        with pytest.raises(
            RuntimeError,
            match="Invalid reorder request: task_ids_to_reorder cannot be empty",
        ):
            driver_service.reorder_tasks(db_session, sim_id, requesting_user, payload)

    def test_reorder_tasks_duplicate_ids_error(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Test reorder with duplicate task IDs raises ValueError."""
        patch_active_simulations["simulator"].reorder_driver_tasks.side_effect = (
            ValueError("contains duplicate task IDs")
        )
        payload = DriverTaskReorderRequest(
            driver_id=1, task_ids=[1, 2], apply_from_top=True
        )
        with pytest.raises(
            RuntimeError, match="Invalid reorder request: contains duplicate task IDs"
        ):
            driver_service.reorder_tasks(db_session, sim_id, requesting_user, payload)

    def test_reorder_tasks_runtime_error(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Test reorder with unexpected runtime error."""
        patch_active_simulations["simulator"].reorder_driver_tasks.side_effect = (
            Exception("Unexpected failure")
        )
        payload = DriverTaskReorderRequest(
            driver_id=1, task_ids=[1, 2], apply_from_top=True
        )
        with pytest.raises(RuntimeError, match="Failed operation: Unexpected failure"):
            driver_service.reorder_tasks(db_session, sim_id, requesting_user, payload)

    def test_reorder_tasks_bottom_mode(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Test task reordering with bottom mode."""
        patch_active_simulations["simulator"].reorder_driver_tasks.return_value = [
            2,
            3,
            1,
        ]
        payload = DriverTaskReorderRequest(
            driver_id=1, task_ids=[1], apply_from_top=False
        )
        response = driver_service.reorder_tasks(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations[
            "simulator"
        ].reorder_driver_tasks.assert_called_once_with(
            sim_id=sim_id, driver_id=1, task_ids_to_reorder=[1], apply_from_top=False
        )
        assert response.task_order == [2, 3, 1]

    def test_batch_assign_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """All assignments succeed and response contains successes."""
        bulk = DriverTaskBatchAssignRequest(driver_id=1, task_ids=[10, 20])
        # simulator batch returns per-item success
        patch_active_simulations[
            "simulator"
        ].batch_assign_tasks_to_driver.return_value = [
            {"task_id": 10, "driver_id": 1, "success": True, "error": None},
            {"task_id": 20, "driver_id": 2, "success": True, "error": None},
        ]
        resp = driver_service.batch_assign(db_session, sim_id, requesting_user, bulk)
        # Accept either 'task_ids' or legacy 'tasks_to_assign' keyword
        call_kwargs = patch_active_simulations[
            "simulator"
        ].batch_assign_tasks_to_driver.call_args.kwargs
        assert call_kwargs.get("sim_id") == sim_id
        assert call_kwargs.get("driver_id") == 1
        assert call_kwargs.get("task_ids", call_kwargs.get("tasks_to_assign")) == [
            10,
            20,
        ]
        assert isinstance(resp, DriverTaskBatchAssignResponse)
        assert len(resp.items) == 2
        assert all(item.success is True for item in resp.items)

    def test_batch_assign_partial_failure(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """If one assignment fails, previous assigns are rolled back."""
        simulator = patch_active_simulations["simulator"]
        # batch returns first success, second failure
        simulator.batch_assign_tasks_to_driver.return_value = [
            {"task_id": 10, "driver_id": 1, "success": True, "error": None},
            {
                "task_id": 20,
                "driver_id": 1,
                "success": False,
                "error": "Could not find task",
            },
        ]

        bulk = DriverTaskBatchAssignRequest(driver_id=1, task_ids=[10, 20])

        resp = driver_service.batch_assign(db_session, sim_id, requesting_user, bulk)

        assert len(resp.items) == 2
        assert resp.items[0].success is True
        assert resp.items[1].success is False
        assert "Could not find task" in (resp.items[1].error or "")
        call_kwargs = patch_active_simulations[
            "simulator"
        ].batch_assign_tasks_to_driver.call_args.kwargs
        assert call_kwargs.get("sim_id") == sim_id
        assert call_kwargs.get("driver_id") == 1
        assert call_kwargs.get("task_ids", call_kwargs.get("tasks_to_assign")) == [
            10,
            20,
        ]

    def test_batch_assign_best_effort_partial(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Best-effort mode returns per-item failures without raising."""
        simulator = patch_active_simulations["simulator"]
        # return a mixed result via the simulator batch API
        simulator.batch_assign_tasks_to_driver.return_value = [
            {"task_id": 10, "driver_id": 1, "success": True, "error": None},
            {
                "task_id": 20,
                "driver_id": 999,
                "success": False,
                "error": "Could not find driver",
            },
        ]

        bulk = DriverTaskBatchAssignRequest(driver_id=1, task_ids=[10, 20])
        resp = driver_service.batch_assign(db_session, sim_id, requesting_user, bulk)

        assert isinstance(resp, DriverTaskBatchAssignResponse)
        assert len(resp.items) == 2
        assert resp.items[0].success is True
        assert resp.items[1].success is False

    def test_batch_assign_permission_denied(
        self, db_session: Session, sim_id: str, requesting_user: int
    ) -> None:
        bulk = DriverTaskBatchAssignRequest(driver_id=1, task_ids=[10])
        with patch.object(simulation_service, "verify_access", return_value=False):
            with pytest.raises(VelosimPermissionError):
                driver_service.batch_assign(db_session, sim_id, requesting_user, bulk)

    def test_batch_assign_simulation_not_found(
        self, db_session: Session, sim_id: str, requesting_user: int
    ) -> None:
        bulk = DriverTaskBatchAssignRequest(driver_id=1, task_ids=[10])
        with patch.object(simulation_service, "active_simulations", {}):
            with pytest.raises(ItemNotFoundError):
                driver_service.batch_assign(db_session, sim_id, requesting_user, bulk)

    def test_batch_unassign_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """All unassignments succeed and return per-item success entries."""
        simulator = patch_active_simulations["simulator"]
        simulator.batch_unassign_tasks_from_drivers.return_value = [
            {"task_id": 10, "driver_id": 1, "success": True, "error": None},
            {"task_id": 20, "driver_id": 2, "success": True, "error": None},
        ]

        bulk = DriverTaskBatchUnassignRequest(task_ids=[10, 20])
        resp = driver_service.batch_unassign(db_session, sim_id, requesting_user, bulk)

        assert isinstance(resp, DriverTaskBatchUnassignResponse)
        assert len(resp.items) == 2
        assert [item.success for item in resp.items] == [True, True]
        assert [item.driver_id for item in resp.items] == [1, 2]
        simulator.batch_unassign_tasks_from_drivers.assert_called_once_with(
            sim_id=sim_id, task_ids=[10, 20]
        )

    def test_batch_unassign_partial_failure(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Best-effort mode reports failures without raising for entire batch."""
        simulator = patch_active_simulations["simulator"]
        simulator.batch_unassign_tasks_from_drivers.return_value = [
            {"task_id": 10, "driver_id": 1, "success": True, "error": None},
            {
                "task_id": 20,
                "driver_id": None,
                "success": False,
                "error": "Task 20 is not assigned to any driver",
            },
        ]

        bulk = DriverTaskBatchUnassignRequest(task_ids=[10, 20])
        resp = driver_service.batch_unassign(db_session, sim_id, requesting_user, bulk)

        assert len(resp.items) == 2
        assert resp.items[0].success is True
        assert resp.items[0].driver_id == 1
        assert resp.items[1].success is False
        assert resp.items[1].driver_id is None
        assert "not assigned to any driver" in (resp.items[1].error or "")

    def test_batch_unassign_result_passthrough(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        """Service maps simulator batch-unassign result fields as-is."""
        simulator = patch_active_simulations["simulator"]
        simulator.batch_unassign_tasks_from_drivers.return_value = [
            {
                "task_id": 10,
                "driver_id": 1,
                "success": False,
                "error": "Some simulator failure",
            }
        ]

        bulk = DriverTaskBatchUnassignRequest(task_ids=[10])
        resp = driver_service.batch_unassign(db_session, sim_id, requesting_user, bulk)

        assert len(resp.items) == 1
        assert resp.items[0].success is False
        assert resp.items[0].driver_id == 1
        assert resp.items[0].error == "Some simulator failure"

    def test_batch_unassign_permission_denied(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
    ) -> None:
        bulk = DriverTaskBatchUnassignRequest(task_ids=[10])
        with patch.object(simulation_service, "verify_access", return_value=False):
            with pytest.raises(VelosimPermissionError):
                driver_service.batch_unassign(db_session, sim_id, requesting_user, bulk)

    def test_batch_unassign_simulation_not_found(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
    ) -> None:
        bulk = DriverTaskBatchUnassignRequest(task_ids=[10])
        with patch.object(simulation_service, "active_simulations", {}):
            with pytest.raises(ItemNotFoundError):
                driver_service.batch_unassign(db_session, sim_id, requesting_user, bulk)

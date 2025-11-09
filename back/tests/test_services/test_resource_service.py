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
from back.services.resource_service import resource_service
from back.services.simulation_service import simulation_service
from back.schemas import (
    ResourceTaskAssignRequest,
    ResourceTaskAssignResponse,
    ResourceTaskUnassignRequest,
    ResourceTaskUnassignResponse,
    ResourceTaskReassignRequest,
    ResourceTaskReassignResponse,
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
        patch.object(
            simulation_service, "verify_access", return_value=True
        ) as mock_verify,
    ):
        yield {"verify_access": mock_verify, "simulator": simulator_mock}


class TestResourceService:
    """Tests for ResourceService using updated active_simulations."""

    def test_assign_task_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        payload = ResourceTaskAssignRequest(resource_id=1, task_id=100)
        response = resource_service.assign_task(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations[
            "simulator"
        ].assign_task_to_resource.assert_called_once_with(
            sim_id=sim_id, task_id=100, resource_id=1
        )
        assert isinstance(response, ResourceTaskAssignResponse)
        assert response.task_id == 100
        assert response.resource_id == 1

    def test_assign_task_permission_denied(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
    ) -> None:
        payload = ResourceTaskAssignRequest(resource_id=1, task_id=100)
        with patch.object(simulation_service, "verify_access", return_value=False):
            with pytest.raises(VelosimPermissionError):
                resource_service.assign_task(
                    db_session, sim_id, requesting_user, payload
                )

    def test_assign_task_not_found(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        patch_active_simulations["simulator"].assign_task_to_resource.side_effect = (
            Exception("Could not find task")
        )
        payload = ResourceTaskAssignRequest(resource_id=1, task_id=100)
        with pytest.raises(ItemNotFoundError, match="Task 100 not found"):
            resource_service.assign_task(db_session, sim_id, requesting_user, payload)

    def test_assign_task_runtime_error(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        patch_active_simulations["simulator"].assign_task_to_resource.side_effect = (
            Exception("Unexpected failure")
        )
        payload = ResourceTaskAssignRequest(resource_id=1, task_id=100)
        with pytest.raises(RuntimeError, match="Failed operation: Unexpected failure"):
            resource_service.assign_task(db_session, sim_id, requesting_user, payload)

    def test_unassign_task_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        payload = ResourceTaskUnassignRequest(resource_id=1, task_id=100)
        response = resource_service.unassign_task(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations[
            "simulator"
        ].unassign_task_from_resource.assert_called_once_with(
            sim_id=sim_id, task_id=100, resource_id=1
        )
        assert isinstance(response, ResourceTaskUnassignResponse)
        assert response.task_id == 100
        assert response.resource_id == 1

    def test_unassign_task_permission_denied(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
    ) -> None:
        payload = ResourceTaskUnassignRequest(resource_id=1, task_id=100)
        with patch.object(simulation_service, "verify_access", return_value=False):
            with pytest.raises(VelosimPermissionError):
                resource_service.unassign_task(
                    db_session, sim_id, requesting_user, payload
                )

    @pytest.mark.parametrize(
        "exception_msg,expected_error",
        [
            ("Could not find task", "Task 100 not found"),
            ("Could not find resource", "Resource 1 not found"),
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
        patch_active_simulations[
            "simulator"
        ].unassign_task_from_resource.side_effect = Exception(exception_msg)
        payload = ResourceTaskUnassignRequest(resource_id=1, task_id=100)
        if "Unexpected" in exception_msg:
            with pytest.raises(RuntimeError, match=expected_error):
                resource_service.unassign_task(
                    db_session, sim_id, requesting_user, payload
                )
        else:
            with pytest.raises(ItemNotFoundError, match=expected_error):
                resource_service.unassign_task(
                    db_session, sim_id, requesting_user, payload
                )

    def test_reassign_task_success(
        self,
        db_session: Session,
        sim_id: str,
        requesting_user: int,
        patch_active_simulations: Dict[str, Any],
    ) -> None:
        payload = ResourceTaskReassignRequest(
            task_id=100, old_resource_id=1, new_resource_id=2
        )
        response = resource_service.reassign_task(
            db_session, sim_id, requesting_user, payload
        )
        patch_active_simulations["simulator"].reassign_task.assert_called_once_with(
            sim_id=sim_id, task_id=100, old_resource_id=1, new_resource_id=2
        )
        assert isinstance(response, ResourceTaskReassignResponse)
        assert response.task_id == 100
        assert response.old_resource_id == 1
        assert response.new_resource_id == 2

    @pytest.mark.parametrize(
        "exception_msg,expected_error",
        [
            ("100", "Task 100 not found"),
            ("1", "Old resource 1 not found"),
            ("2", "New resource 2 not found"),
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
        payload = ResourceTaskReassignRequest(
            task_id=100, old_resource_id=1, new_resource_id=2
        )
        if "Unexpected" in exception_msg:
            with pytest.raises(RuntimeError, match=expected_error):
                resource_service.reassign_task(
                    db_session, sim_id, requesting_user, payload
                )
        else:
            with pytest.raises(ItemNotFoundError, match=expected_error):
                resource_service.reassign_task(
                    db_session, sim_id, requesting_user, payload
                )

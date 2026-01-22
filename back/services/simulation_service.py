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

from typing import TYPE_CHECKING, Dict, List, NotRequired, TypedDict
import asyncio
from sqlalchemy.orm import Session
from back.core.simulation_callbacks import on_simulation_completed
from back.models import User
from back.models.sim_instance import SimInstance
from back.models.sim_frame import SimFrame
from back.schemas import (
    PlaybackSpeedBase,
    PlaybackSpeedResponse,
    SimulationPlaybackStatus,
)
from back.schemas.sim_frame import (
    SeekResponse,
    SeekPosition,
    FrameWindow,
    SimulationState,
    SimFrameResponse,
)
from sim.core.simulation_environment import SimulationEnvironment
from sim.simulator import Simulator
from sim.entities.inputParameters import InputParameter
from back.crud import sim_instance_crud, user_crud, sim_frame_crud
from back.schemas.sim_instance import (
    SimInstanceCreate,
    SimulationResponse,
    BranchResponse,
)
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.core.config import settings
from grafana_logging.logger import get_logger
from back.services.frame_persistence_service import FramePersistenceSubscriber
from back.services.simulation_data_service import SimulationDataService


from sim.utils.replay_parser import ReplayParser

logger = get_logger(__name__)

if TYPE_CHECKING:
    from back.api.v1.utils.sim_websocket_helpers import WebSocketSubscriber


class SimulationLockManager:
    """Manages per-simulation locks for thread-safe operations."""

    _locks: Dict[str, asyncio.Lock] = {}

    @classmethod
    def get_lock(cls, sim_id: str) -> asyncio.Lock:
        """Get or create lock for simulation.

        Args:
            sim_id: The UUID of the simulation to get the lock for

        Returns:
            asyncio.Lock instance for the specified simulation
        """
        if sim_id not in cls._locks:
            cls._locks[sim_id] = asyncio.Lock()
        return cls._locks[sim_id]

    @classmethod
    def remove_lock(cls, sim_id: str) -> None:
        """Remove lock when simulation is cleaned up.

        Args:
            sim_id: The UUID of the simulation to remove the lock for

        Returns:
            None
        """
        cls._locks.pop(sim_id, None)


class ActiveSimulationData(TypedDict):
    """Type definition for active simulation data stored in memory."""

    # Required attributes
    db_id: int  # links to database record
    status: str  # tracks simulation state
    sim_time: int | None  # duration (assigned None if undefined)
    user_id: int  # identifies simulation owner
    # Optional attributes
    ws_subscriber: NotRequired["WebSocketSubscriber"]  # WebSocket connected
    shutdown_task: NotRequired["asyncio.Task"]  # Auto-shutdown scheduled
    initialization_start_time: NotRequired[
        float
    ]  # Records start time of initialization, used for startup metrics
    keyframe_subscriber: NotRequired[FramePersistenceSubscriber]  # Keyframe persistence
    restored_keyframe: NotRequired[dict]  # Persisted keyframe used for restoration
    paused_by_user: NotRequired[
        bool
    ]  # True if paused by user (vs auto-paused on disconnect)


class SimulationService:
    """Service layer for managing the lifecycle and access control of simulations."""

    def __init__(self) -> None:
        # Maps sim_id (UUID from simulator) -> ActiveSimulationData
        self.active_simulations: Dict[str, ActiveSimulationData] = {}
        self.simulator = Simulator()
        self.simulation_data_service = SimulationDataService()

    # Internal helper
    def _get_requesting_user(self, db: Session, requesting_user: int) -> User:
        """
        Attempt to fetch and validate the requesting user.

        This method retrieves the user from the database by their ID, verifying
        that the account exists and is currently enabled. It raises an
        ItemNotFoundError if the user does not exist or a VelosimPermissionError
        if the user is disabled.
        """
        user = user_crud.get(db, requesting_user)
        if not user:
            raise ItemNotFoundError("Requesting user not found.")
        if not user.is_enabled:
            raise VelosimPermissionError("Requesting user is disabled.")
        return user

    def verify_access(self, db: Session, sim_id: str, requesting_user: int) -> bool:
        """
        Return True if the requesting user has permission to access the simulation
        identified by its in-memory UUID.

        Admins always have permission, otherwise the requesting user must be the
        owner of that simulation instance.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation to verify access for.
            requesting_user: The ID of the user requesting access.

        Returns:
            bool: True if user has access, False otherwise.

        Raises:
            ItemNotFoundError: if the simulation is not found, either in-memory
                or from its database record.
        """
        user = self._get_requesting_user(db, requesting_user)

        sim_data = self.ensure_active_simulation(
            sim_id=sim_id, db=db, requesting_user=requesting_user
        )

        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if not db_sim_instance:
            raise ItemNotFoundError(f"Simulation instance record {db_id} not found")

        return user.is_admin or db_sim_instance.user_id == user.id

    def ensure_active_simulation(
        self, sim_id: str, db: Session, requesting_user: int
    ) -> ActiveSimulationData:
        """
        Retrieve an active simulation instance by its in-memory simulation ID.

        This method looks up the simulation in the active simulations registry and
        returns its associated ActiveSimulationData object.

        Args:
            sim_id (str): The in-memory UUID of the active simulation.

        Returns:
            ActiveSimulationData: The active simulation data associated with the
            given simulation ID.

        Raises:
            ItemNotFoundError: If no active simulation exists with the provided ID.
        """

        sim_data = self.active_simulations.get(sim_id)

        if sim_data:
            return sim_data

        return self.restore_simulation(db, sim_id, requesting_user)

    def restore_simulation(
        self, db: Session, sim_id: str, requesting_user: int
    ) -> ActiveSimulationData:
        """
        Restore a simulation from its persisted state.

        Args:
            sim_id (str): The ID of the simulation to restore.

        Returns:
            None
        """

        user = self._get_requesting_user(db, requesting_user)

        db_sim = sim_instance_crud.get_by_uuid(db, sim_id)

        if not db_sim:
            raise ItemNotFoundError(f"Simulation {sim_id} not found")

        if db_sim.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to restore simulation")

        scenario = self.simulation_data_service.get_scenario(db, sim_id)
        keyframe = self.simulation_data_service.get_last_persisted_keyframe(db, sim_id)

        resume_state = ReplayParser.parse(
            scenario_json=scenario,
            keyframe_json=keyframe,
        )

        input_params = resume_state.input_parameters
        map_controller = resume_state.map_controller
        current_sim_time = resume_state.current_time_seconds
        real_time_factor = resume_state.real_time_factor
        should_auto_resume = resume_state.should_auto_resume

        sim = self.simulator

        frame_subscriber = FramePersistenceSubscriber(db_sim.id)
        frame_subscriber.start()

        env = SimulationEnvironment()

        env.run(until=current_sim_time)

        restore_sim_id = sim.initialize(
            input_params,
            subscribers=[frame_subscriber],
            run_id=sim_id,
            map_controller=map_controller,
            env=env,
            initial_running=should_auto_resume,
            real_time_factor=real_time_factor,
            on_completed_callback=on_simulation_completed,
        )

        self.active_simulations[restore_sim_id] = ActiveSimulationData(
            db_id=db_sim.id,
            status="resumed",
            sim_time=input_params.sim_time,
            user_id=db_sim.user_id,
            keyframe_subscriber=frame_subscriber,
            restored_keyframe=keyframe,
            paused_by_user=resume_state.paused_by_user,
        )

        return self.active_simulations[restore_sim_id]

    def initialize_simulation(
        self,
        db: Session,
        requesting_user: int,
        params: InputParameter,
        scenario_payload: dict | None = None,
    ) -> SimulationResponse:
        """Initialize a new simulation with the given parameters.

        Args:
            db: Database session.
            requesting_user: The ID of the user initializing the simulation.
            params: Input parameters for the simulation.
            scenario_payload: Original scenario payload to persist for future restarts.

        Returns:
            SimulationResponse: Response containing sim_id, db_id, and status.
        """
        user = self._get_requesting_user(db, requesting_user)

        # Create DB record
        sim_instance_data = SimInstanceCreate(
            user_id=user.id, scenario_payload=scenario_payload
        )
        db_sim_instance = sim_instance_crud.create(db, sim_instance_data)

        # Create a fresh Simulator for this simulation
        sim = self.simulator

        # Create frame persistence subscriber
        frame_subscriber = FramePersistenceSubscriber(db_sim_instance.id)
        frame_subscriber.start()

        # Initialize simulation with InputParameter and persistence subscriber
        sim_id = sim.initialize(
            params,
            subscribers=[frame_subscriber],
            on_completed_callback=on_simulation_completed,
        )

        # Update the database record with the simulator's UUID
        db_sim_instance.uuid = sim_id
        db.commit()

        # Store the simulation data per sim_id
        self.active_simulations[sim_id] = ActiveSimulationData(
            db_id=db_sim_instance.id,
            status="initialized",
            sim_time=params.sim_time,
            user_id=user.id,
            keyframe_subscriber=frame_subscriber,
        )

        return SimulationResponse(
            sim_id=sim_id,
            db_id=db_sim_instance.id,
            status="initialized",
        )

    def start_simulation(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
    ) -> SimulationResponse:
        """
        Start an initialized simulation and return a confirmation response.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation to start.
            requesting_user: The ID of the user starting the simulation.

        Returns:
            SimulationResponse: Response containing sim_id, db_id, and running status.
        """
        if not self.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError("Unauthorized to start this simulation.")

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]

        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        # Use the Simulator instance tied to this sim
        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")

        # Ensure the sim actually contains this sim_id
        sim_info = sim.get_sim_by_id(sim_id)
        if sim_info is None:
            raise RuntimeError(f"Simulation {sim_id} not found in its Simulator")

        sim_time_value = sim_data.get("sim_time")
        if sim_time_value is None:
            raise ValueError(
                f"Simulation {sim_id} does not have a valid sim_time defined."
            )

        sim.start(sim_id, sim_time_value)

        # Update state
        sim_data["status"] = "running"

        return SimulationResponse(
            sim_id=sim_id,
            db_id=db_sim_instance.id,
            status="running",
        )

    def stop_simulation(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
    ) -> bool:
        """
        Stop a simulation by ID (owner or admin only).

        Args:
            db: Database session
            sim_id: The simulator UUID
            requesting_user: Requesting user's ID
        Returns:
            True if stopped successfully
        Raises:
            ItemNotFoundError if not found
            VelosimPermissionError if unauthorized
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        assert db_sim_instance is not None

        # Authorization check
        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to stop this simulation.")

        # Stop simulator (keep DB record for historical access and future resume)
        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        sim.stop(sim_id)

        # Shutdown keyframe persistence subscriber if present
        if "keyframe_subscriber" in sim_data:
            keyframe_sub = sim_data["keyframe_subscriber"]
            try:
                # Run async shutdown in the event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(keyframe_sub.shutdown())
                else:
                    loop.run_until_complete(keyframe_sub.shutdown())
            except Exception as e:
                logger.error(
                    f"Failed to shutdown keyframe subscriber for {sim_id}: {e}"
                )

        del self.active_simulations[sim_id]
        # Clean up the lock for this simulation
        SimulationLockManager.remove_lock(sim_id)
        return True

    def get_active_user_simulations(
        self, db: Session, requesting_user: int, skip: int = 0, limit: int = 10
    ) -> tuple[List[SimInstance], int]:
        """
        Retrieve simulations owned by the requesting user with pagination.

        Args:
            db: Database session
            requesting_user: Requesting user's ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of SimInstance objects, total count)
        """
        user = self._get_requesting_user(db, requesting_user)

        if not self.active_simulations:
            return [], 0

        db_ids = [int(data["db_id"]) for data in self.active_simulations.values()]
        all_instances = (
            db.query(SimInstance)
            .filter(SimInstance.id.in_(db_ids), SimInstance.user_id == user.id)
            .all()
        )

        total = len(all_instances)
        paginated = all_instances[skip : skip + limit]

        return paginated, total

    def get_all_active_simulations(
        self, db: Session, requesting_user: int, skip: int = 0, limit: int = 10
    ) -> tuple[List[SimInstance], int]:
        """
        Retrieve all active simulations with pagination.
        This is an admin-only operation.

        Args:
            db: Database session
            requesting_user: Requesting user's ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of SimInstance objects, total count)
        """
        user = self._get_requesting_user(db, requesting_user)
        if not user.is_admin:
            raise VelosimPermissionError(
                "Admin privileges required to list all active simulations."
            )

        # Batch fetch all sim_instances in a single query
        if not self.active_simulations:
            return [], 0

        db_ids = [int(data["db_id"]) for data in self.active_simulations.values()]
        all_instances = db.query(SimInstance).filter(SimInstance.id.in_(db_ids)).all()

        total = len(all_instances)
        paginated = all_instances[skip : skip + limit]

        return paginated, total

    def get_all_user_simulations(
        self,
        db: Session,
        requesting_user: int,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[List[SimInstance], int]:
        """
        Retrieve all simulations (active and inactive) with pagination.

        Admins see all simulations.
        Non-admin users see only their own simulations.

        Args:
            db: Database session
            requesting_user: Requesting user's ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of SimInstance objects, total count)
        """

        user = self._get_requesting_user(db, requesting_user)

        query = db.query(SimInstance)

        # Queries user-specific simulations.
        query = query.filter(SimInstance.user_id == user.id)

        total = query.count()

        simulations = (
            query.order_by(
                SimInstance.date_created.desc()
            )  # Returning by most recent sims.
            .offset(skip)
            .limit(limit)
            .all()
        )
        return simulations, total

    def get_simulation_status(
        self, db: Session, sim_id: str, requesting_user: int
    ) -> str:
        """
        Get status of a specific simulation.

        Admins can query the status of any simulation, whereas non-admin users
        can only query their own.

        Args:
            db: Database session
            sim_id: Simulator UUID
            requesting_user: Requesting user's ID

        Returns:
            string representing the simulation status
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        assert db_sim_instance is not None

        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to access this simulation.")

        return str(sim_data["status"])

    def _stop_all_simulations_core(self, db: Session) -> None:
        """
        Core logic to stop all running simulations and clean up DB records. Does
        not perform any permission checks so it can be called by system code.
        """
        try:
            # Stop all simulators
            sim = self.simulator

            for sim_id in list(self.active_simulations.keys()):
                try:
                    sim.stop(sim_id)
                except Exception as exc:
                    logger.error(f"Failed to stop simulation {sim_id}: {exc}")

            # Clean up database records in a single batch operation
            if self.active_simulations:
                db_ids = [
                    int(data["db_id"]) for data in self.active_simulations.values()
                ]
                db.query(SimInstance).filter(SimInstance.id.in_(db_ids)).delete(
                    synchronize_session=False
                )

            db.commit()
            self.active_simulations.clear()

            # Clean up all locks after simulations are stopped
            for sim_id in list(SimulationLockManager._locks.keys()):
                SimulationLockManager.remove_lock(sim_id)

        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to stop all simulations: {exc}") from exc

    def stop_all_simulations(self, db: Session, requesting_user: int) -> None:
        """
        Stop all running simulations and clean up database records.

        This is an admin-only operation.

        Args:
            db: Database session
            requesting_user: Requesting user's ID

        Returns:
            None
        """
        user = self._get_requesting_user(db, requesting_user)
        if not user.is_admin:
            raise VelosimPermissionError("Only admins can stop all simulations.")

        self._stop_all_simulations_core(db)

    def stop_all_simulations_system(self, db: Session) -> None:
        """
        Stop all running simulations from system context (ex. during shutdown).

        No user check. Use carefully.

        Args:
            db: Database session.

        Returns:
            None
        """
        self._stop_all_simulations_core(db)

    def set_playback_speed(
        self,
        db: Session,
        sim_id: str,
        playback_speed: PlaybackSpeedBase,
        requesting_user: int,
    ) -> PlaybackSpeedResponse:
        """Set the playback speed for a simulation.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation.
            playback_speed: The new playback speed settings.
            requesting_user: The ID of the user making the request.

        Returns:
            PlaybackSpeedResponse: Response containing the updated playback speed.
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to modify this simulation.")

        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        sim_info = sim.get_sim_by_id(sim_id)
        if sim_info is None:
            raise RuntimeError(f"Simulation {sim_id} not found in simulator")
        sim_controller = sim_info["simController"]
        driver = sim_controller.realTimeDriver

        # Adjust playback based on requested speed
        speed_value = playback_speed.playback_speed

        if speed_value == 0:  # the requested value is equivalent to pausing
            # Check if sim was already paused (e.g., by cleanup_simulation)
            # If already paused and paused_by_user is False (auto-pause), don't
            # override it with paused_by_user=True - that would break auto-resume
            already_paused = not driver.running
            was_auto_paused = already_paused and not sim_data.get(
                "paused_by_user", False
            )

            driver.pause()

            if was_auto_paused:
                # Sim was auto-paused, don't emit a user-pause keyframe
                # This prevents late playbackSpeed=0 calls from breaking auto-resume
                pass
            else:
                # This is a genuine user pause action
                sim_data["paused_by_user"] = True
                # Emit and force-persist a keyframe on pause to capture current state
                keyframe = sim_controller.create_frame(is_key=True, paused_by_user=True)
                sim_controller.emit_frame(keyframe)
                # Also force immediate persistence, bypassing interval filtering
                keyframe_subscriber = sim_data.get("keyframe_subscriber")
                if keyframe_subscriber:
                    keyframe_subscriber.force_persist_keyframe(keyframe)
        else:  # handle any other valid playback speed properly
            # Set speed first, then resume if needed
            inverted_factor = 1.0 / speed_value
            driver.set_real_time_factor(inverted_factor)
            driver.resume()

        status = (
            SimulationPlaybackStatus.RUNNING
            if driver.running
            else SimulationPlaybackStatus.PAUSED
        )

        return PlaybackSpeedResponse(
            simulation_id=sim_id, playback_speed=speed_value, status=status
        )

    def get_playback_speed(
        self,
        db: Session,
        sim_id: str,
        requesting_user: int,
    ) -> PlaybackSpeedResponse:
        """
        Return the current playback speed and runtime status for a simulation.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation.
            requesting_user: The ID of the user making the request.

        Returns:
            PlaybackSpeedResponse: Response containing the current playback
                speed and status.
        """
        user = self._get_requesting_user(db, requesting_user)

        if sim_id not in self.active_simulations:
            raise ItemNotFoundError(sim_id, "Simulation not found")

        sim_data = self.active_simulations[sim_id]
        db_id: int = sim_data["db_id"]
        db_sim_instance = sim_instance_crud.get(db, db_id)
        if db_sim_instance is None:
            raise ItemNotFoundError(db_id, "Simulation instance record not found")

        if db_sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError("Unauthorized to access this simulation.")

        # Get simulator runtime information from the sim package
        sim = self.simulator
        if sim is None:
            raise RuntimeError(f"Simulator for simulation {sim_id} not found")
        sim_info = sim.get_sim_by_id(sim_id)
        # Retrieve the corresponding realTimeDriver
        driver = sim_info["simController"].realTimeDriver  # type: ignore

        # Determine status based on the boolean value of 'running' attribute
        # from realTimeDriver
        status = (
            SimulationPlaybackStatus.RUNNING
            if driver.running
            else SimulationPlaybackStatus.PAUSED
        )

        return PlaybackSpeedResponse(
            simulation_id=sim_id,
            playback_speed=float(driver.real_time_factor),
            status=status,
        )

    def seek_to_position(
        self,
        db: Session,
        sim_id: str,
        position: float,
        frame_window_seconds: float,
        playback_speed: float | None,
        requesting_user: int,
    ) -> SeekResponse:
        """Seek to a specific position in a simulation's timeline.

        This method handles the business logic for seeking in both running and
        stopped simulations, retrieving appropriate frames from the database.

        Args:
            db: Database session.
            sim_id: The UUID of the simulation.
            position: Target simulation time in seconds (>= 0).
            frame_window_seconds: Number of simulation seconds of future frames
                to return.
            playback_speed: Optional playback speed to set (>= 0). If provided,
                updates the simulation's playback speed (only for running sims).
            requesting_user: The ID of the user making the request.

        Returns:
            SeekResponse containing position info, frames, and simulation state.

        Raises:
            ItemNotFoundError: If simulation or user not found.
            VelosimPermissionError: If user not authorized to access simulation.
        """
        user = self._get_requesting_user(db, requesting_user)

        # Determine if simulation is running and get database ID
        db_id: int
        current_sim_seconds: float
        is_running = False

        sim_instance: SimInstance | None = None
        try:
            if sim_id in self.active_simulations:
                sim_data = self.active_simulations[sim_id]
                db_id = sim_data["db_id"]
                is_running = True

                # Get current simulation time from running simulation
                sim_info = self.simulator.get_sim_by_id(sim_id)
                if sim_info:
                    current_sim_seconds = sim_info[
                        "simController"
                    ].clock.sim_time_seconds
                else:
                    # Fallback if sim not found in simulator
                    current_sim_seconds = position
        except (KeyError, AttributeError):
            # Simulation was deleted/stopped between check and access
            is_running = False

        if not is_running:
            # Fallback to database for historical simulations
            sim_instance = sim_instance_crud.get_by_uuid(db, sim_id)
            if not sim_instance:
                raise ItemNotFoundError("Simulation not found")
            db_id = sim_instance.id
            # For stopped simulations, compute from latest frame
            current_sim_seconds = position

        logger.debug(
            f"initial state - sim_id={sim_id}, is_running={is_running}, "
            f"db_id={db_id}, current_sim_seconds={current_sim_seconds}"
        )

        # Verify simulation exists and check authorization (reuse if already fetched)
        if sim_instance is None:
            sim_instance = sim_instance_crud.get(db, db_id)
        if not sim_instance:
            raise ItemNotFoundError("Simulation not found")

        if sim_instance.user_id != user.id and not user.is_admin:
            raise VelosimPermissionError(
                "Unauthorized to access this simulation's frames"
            )

        # Update playback speed if requested (only for running simulations)
        current_playback_speed = 0.0  # Default, not running
        if playback_speed is not None and is_running:
            playback_response = self.set_playback_speed(
                db=db,
                sim_id=sim_id,
                playback_speed=PlaybackSpeedBase(playback_speed=playback_speed),
                requesting_user=requesting_user,
            )
            current_playback_speed = playback_response.playback_speed
        elif is_running:
            # Get current playback speed from running simulation
            playback_response = self.get_playback_speed(
                db=db, sim_id=sim_id, requesting_user=requesting_user
            )
            # Extract just the float value, don't use the response object directly
            # since it may contain values outside the validation range
            current_playback_speed = float(playback_response.playback_speed)

        # Find the keyframe at or before the requested position
        keyframe = sim_frame_crud.get_keyframe_at_or_before(db, db_id, position)

        if keyframe is None:
            # No keyframe found - return empty response
            # For running sims: never at live edge (sim is generating new frames)
            # For stopped sims: at live edge if no frames exist in DB
            return SeekResponse(
                position=SeekPosition(sim_id=sim_id, target_sim_seconds=position),
                frames=FrameWindow(
                    initial_frames=[],
                    future_frames=[],
                    has_more_frames=False,
                ),
                state=SimulationState(
                    current_sim_seconds=current_sim_seconds,
                    is_at_live_edge=not is_running,
                    playback_speed=current_playback_speed,
                ),
            )

        # Get diff frames between keyframe and position (exclusive start)
        keyframe_time = keyframe.sim_seconds_elapsed
        diff_frames_to_position = sim_frame_crud.get_frames_in_range(
            db=db,
            sim_instance_id=db_id,
            start_time=keyframe_time,
            end_time=position,
            include_start=False,  # Don't include the keyframe again
        )

        # Build initial_frames: keyframe first, then diffs in order
        initial_frames = [SimFrameResponse.model_validate(keyframe)]
        initial_frames.extend(
            [SimFrameResponse.model_validate(f) for f in diff_frames_to_position]
        )

        # Get future frames from position to position + window (inclusive start)
        frame_window_end = position + frame_window_seconds
        logger.debug(
            f"sim_id={sim_id}, position={position}, window={frame_window_seconds}, "
            f"frame_window_end={frame_window_end}, is_running={is_running}, "
            f"initial_current_sim_seconds={current_sim_seconds}"
        )

        future_frames_list = sim_frame_crud.get_frames_in_range(
            db=db,
            sim_instance_id=db_id,
            start_time=position,
            end_time=frame_window_end,
            include_start=True,  # Include frames at exactly position
        )
        logger.debug(
            f"sim_id={sim_id}, Got {len(future_frames_list)} future frames "
            f"from {position} to {frame_window_end}"
        )

        future_frames = [SimFrameResponse.model_validate(f) for f in future_frames_list]

        # Check if there are more frames beyond the window using efficient LIMIT 1 query
        has_more_frames = sim_frame_crud.has_frames_after(
            db=db,
            sim_instance_id=db_id,
            after_time=frame_window_end,
        )
        logger.debug(
            f"sim_id={sim_id}, has_more_frames={has_more_frames} "
            f"(checked beyond {frame_window_end})"
        )

        # Determine if we're at the live edge
        # For stopped sims: at live edge if no more frames exist in DB
        # For running sims: at live edge if no frames beyond window AND last future
        # frame is at or near current sim time
        is_at_live_edge = False

        if not is_running:
            # Stopped sim: simply check if no more frames
            is_at_live_edge = not has_more_frames
        else:
            # Running sim: at live edge if no frames beyond window AND
            # we have future frames that extend to/near current sim time
            if not has_more_frames and future_frames_list:
                last_frame_time = future_frames_list[-1].sim_seconds_elapsed
                # At live edge if last frame is within threshold of current time
                threshold = settings.LIVE_EDGE_THRESHOLD_SECONDS
                is_at_live_edge = (
                    abs(last_frame_time - current_sim_seconds) <= threshold
                )

        if not is_running:
            # Update current_sim_seconds based on the latest frame we have
            if future_frames_list:
                current_sim_seconds = max(
                    current_sim_seconds, future_frames_list[-1].sim_seconds_elapsed
                )

        return SeekResponse(
            position=SeekPosition(sim_id=sim_id, target_sim_seconds=position),
            frames=FrameWindow(
                initial_frames=initial_frames,
                future_frames=future_frames,
                has_more_frames=has_more_frames,
            ),
            state=SimulationState(
                current_sim_seconds=current_sim_seconds,
                is_at_live_edge=is_at_live_edge,
                playback_speed=current_playback_speed,
            ),
        )

    def branch_simulation(
        self,
        db: Session,
        sim_id: str,
        keyframe_seq: int,
        name: str | None,
        requesting_user: int,
    ) -> BranchResponse:
        """Branch a simulation from a specific keyframe.

        Creates a new simulation instance with frames copied from the source
        simulation up to and including the specified keyframe. If the provided
        seq_number is not a keyframe, the most recent prior keyframe is used.

        Args:
            db: Database session.
            sim_id: UUID of the source simulation to branch from.
            keyframe_seq: The seq_number to branch from (will use prior keyframe
                if not a keyframe).
            name: Optional name for the new simulation.
            requesting_user: User ID making the request.

        Returns:
            BranchResponse: Details of the newly created branched simulation.

        Raises:
            ItemNotFoundError: If source simulation not found or has no frames.
            VelosimPermissionError: If user lacks permission to access source sim.
            ValueError: If no keyframes exist in the source simulation.
        """
        # 1. Validate source simulation exists and user has access
        source_sim = sim_instance_crud.get_by_uuid(db, sim_id)
        if not source_sim:
            raise ItemNotFoundError(f"Simulation {sim_id} not found")

        # Verify user has permission to access the source simulation
        if not self.verify_access(db, sim_id, requesting_user):
            raise VelosimPermissionError(
                f"User {requesting_user} does not have permission to access "
                f"simulation {sim_id}"
            )

        # 2. Find the actual keyframe to branch from
        # If keyframe_seq doesn't point to a keyframe, find the prior one
        actual_keyframe = (
            db.query(SimFrame)
            .filter(
                SimFrame.sim_instance_id == source_sim.id,
                SimFrame.seq_number <= keyframe_seq,
                SimFrame.is_key == True,  # noqa: E712
            )
            .order_by(SimFrame.seq_number.desc())
            .first()
        )

        if not actual_keyframe:
            raise ValueError(
                f"No keyframes found in simulation {sim_id} at or before "
                f"seq_number {keyframe_seq}"
            )

        actual_keyframe_seq = actual_keyframe.seq_number
        keyframe_data = actual_keyframe.frame_data

        # 3. Validate keyframe can be parsed before creating DB entry
        # Use scenario from source_sim to avoid redundant DB call
        scenario = source_sim.scenario_payload
        if scenario is None:
            raise ValueError(f"Source simulation {sim_id} has no scenario payload")

        try:
            resume_state = ReplayParser.parse(
                scenario_json=scenario,
                keyframe_json=keyframe_data,
            )
        except Exception as e:
            raise ValueError(
                f"Failed to parse keyframe {actual_keyframe_seq} from "
                f"simulation {sim_id}: {str(e)}"
            )

        input_params = resume_state.input_parameters
        map_controller = resume_state.map_controller
        current_sim_time = resume_state.current_time_seconds

        # 4. Create new SimInstance with branching metadata
        new_sim_data = SimInstanceCreate(
            user_id=requesting_user,
            scenario_payload=source_sim.scenario_payload,
            name=name,
            parent_sim_instance_id=source_sim.id,
            branch_keyframe_seq=actual_keyframe_seq,
        )

        new_sim = sim_instance_crud.create(db, new_sim_data)
        db.flush()  # Get ID without committing transaction

        # 5. Copy frames from source to new simulation
        frames_copied = sim_frame_crud.copy_frames_to_new_instance(
            db,
            source_sim_instance_id=source_sim.id,
            target_sim_instance_id=new_sim.id,
            max_seq=actual_keyframe_seq,
        )

        logger.info(
            f"Branched simulation {new_sim.id} from {sim_id} at keyframe "
            f"seq {actual_keyframe_seq}. Copied {frames_copied} frames."
        )

        # 6. Initialize simulator with the branched keyframe state (paused)
        # Wrap in try/except to ensure cleanup on failure
        try:
            # Create simulation environment and advance to branch point
            env = SimulationEnvironment()
            env.run(until=current_sim_time + input_params.start_time)

            # Create frame persistence subscriber AFTER successful environment creation
            frame_subscriber = FramePersistenceSubscriber(new_sim.id)
            frame_subscriber.start()

            # Initialize simulator in paused state
            sim = self.simulator
            branch_sim_id = sim.initialize(
                input_params,
                subscribers=[frame_subscriber],
                run_id=new_sim.uuid,
                map_controller=map_controller,
                env=env,
                initial_running=False,
                real_time_factor=0.0,
            )

            # Store in active simulations only after successful initialization
            self.active_simulations[branch_sim_id] = ActiveSimulationData(
                db_id=new_sim.id,
                status="initialized",  # Initialized but paused
                sim_time=input_params.sim_time,
                user_id=requesting_user,
                keyframe_subscriber=frame_subscriber,
                restored_keyframe=keyframe_data,
                paused_by_user=True,  # Explicitly paused
            )

            # Commit transaction only after successful initialization
            db.commit()
            db.refresh(new_sim)

            logger.info(
                f"Initialized branched simulation {branch_sim_id} in paused state"
            )
        except Exception as e:
            # Rollback database changes if initialization fails
            db.rollback()
            logger.error(
                f"Failed to initialize branched simulation from {sim_id}: {str(e)}"
            )
            raise

        # 6. Return BranchResponse with the generated UUID
        # Assertion for type check
        assert new_sim.uuid is not None, "branched sim does not have an ID"
        return BranchResponse(
            sim_id=new_sim.uuid,
            db_id=new_sim.id,
            name=new_sim.name,
            branched_from_sim_id=source_sim.uuid or f"sim-{source_sim.id}",
            branched_from_keyframe_seq=actual_keyframe_seq,
            status="initialized",  # Changed from "created" to "initialized"
        )


# Global simulation service instance
simulation_service = SimulationService()

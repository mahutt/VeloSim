# Import all CRUD classes here for easy access
from .station import station_crud
from .station_task import station_task_crud

__all__ = ["station_crud", "station_task_crud"]

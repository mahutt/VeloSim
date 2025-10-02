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

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from back.models.station import Station
from back.schemas.station import StationCreate, StationUpdate


class StationCRUD:
    """CRUD operations for Station model."""

    def create(self, db: Session, station_data: StationCreate) -> Station:
        """Create a new station."""
        db_station = Station(
            name=station_data.name,
            longitude=station_data.longitude,
            latitude=station_data.latitude,
        )
        db.add(db_station)
        db.flush()
        db.refresh(db_station)
        return db_station

    def get(self, db: Session, station_id: int) -> Optional[Station]:
        """Get a station by ID."""
        return db.query(Station).filter(Station.id == station_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Station]:
        """Get a station by name."""
        return db.query(Station).filter(Station.name == name).first()

    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Station], int]:
        """Get all stations with pagination."""
        total = db.query(func.count(Station.id)).scalar() or 0
        stations = db.query(Station).offset(skip).limit(limit).all()
        return stations, total

    def update(
        self, db: Session, station_id: int, station_data: StationUpdate
    ) -> Optional[Station]:
        """Update a station."""
        db_station = self.get(db, station_id)
        if not db_station:
            return None

        update_data = station_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_station, field, value)

        db.flush()
        db.refresh(db_station)
        return db_station

    def delete(self, db: Session, station_id: int) -> bool:
        """Delete a station."""
        db_station = self.get(db, station_id)
        if not db_station:
            return False

        db.delete(db_station)
        db.flush()
        return True


# Create a singleton instance
station_crud = StationCRUD()

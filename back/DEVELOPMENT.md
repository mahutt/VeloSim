# Backend Development Workflow

## 🎯 Overview

The VeloSim backend follows a layered architecture pattern:

1. **Models** - SQLAlchemy database models
2. **Schemas** - Pydantic request/response validation
3. **CRUD** - Database operations
4. **API** - FastAPI route endpoints
5. **Migration** - Database schema changes

## 🚀 Step-by-Step Feature Implementation

### Example: Adding Station Management

Let's walk through creating a complete Station feature from scratch.

### Step 1: Create the SQLAlchemy Model

Define your database table structure:

```python
# back/models/station.py
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from back.database.session import Base

class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Station(id={self.id}, name='{self.name}')>"
```

**Key Points:**

- Extend `Base` from `back.database.session`
- Use appropriate SQLAlchemy column types
- Add indexes for frequently queried fields
- Include timestamps for auditing
- Add a meaningful `__repr__` method

### Step 2: Create Pydantic Schemas

Define request/response validation:

```python
# back/schemas/station.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

class StationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)
    capacity: int = Field(default=10, ge=1, le=100)

class StationCreate(StationBase):
    pass

class StationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    capacity: Optional[int] = Field(None, ge=1, le=100)

class StationResponse(StationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StationListResponse(BaseModel):
    stations: List[StationResponse]
    total: int
    page: int
    size: int
```

**Key Points:**

- Use `Field()` for validation constraints
- Create separate schemas for create/update/response
- Use `from_attributes = True` for SQLAlchemy model compatibility
- Add pagination support for list responses

### Step 3: Create CRUD Operations

Implement database operations:

```python
# back/crud/station.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from back.models.station import Station
from back.schemas.station import StationCreate, StationUpdate

class StationCRUD:
    def create(self, db: Session, station_data: StationCreate) -> Station:
        station = Station(**station_data.dict())
        db.add(station)
        db.commit()
        db.refresh(station)
        return station

    def get_by_id(self, db: Session, station_id: int) -> Optional[Station]:
        return db.query(Station).filter(Station.id == station_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Station]:
        return db.query(Station).filter(Station.name == name).first()

    def get_all(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Station]:
        query = db.query(Station)

        if search:
            query = query.filter(Station.name.ilike(f"%{search}%"))

        return query.offset(skip).limit(limit).all()

    def count(self, db: Session, search: Optional[str] = None) -> int:
        query = db.query(func.count(Station.id))

        if search:
            query = query.filter(Station.name.ilike(f"%{search}%"))

        return query.scalar()

    def update(
        self,
        db: Session,
        station_id: int,
        station_data: StationUpdate
    ) -> Optional[Station]:
        station = self.get_by_id(db, station_id)
        if not station:
            return None

        update_data = station_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(station, field, value)

        db.commit()
        db.refresh(station)
        return station

    def delete(self, db: Session, station_id: int) -> bool:
        station = self.get_by_id(db, station_id)
        if not station:
            return False

        db.delete(station)
        db.commit()
        return True

# Create instance to use in API routes
station_crud = StationCRUD()
```

**Key Points:**

- Include standard CRUD operations (Create, Read, Update, Delete)
- Add search and pagination support
- Use `exclude_unset=True` for partial updates
- Always commit and refresh after modifications
- Return appropriate types (`Optional`, `List`, etc.)

### Step 4: Create API Endpoints

Define FastAPI routes:

```python
# back/api/v1/stations.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from back.database.session import get_db
from back.crud.station import station_crud
from back.schemas.station import (
    StationCreate,
    StationUpdate,
    StationResponse,
    StationListResponse
)

router = APIRouter()

@router.post("/", response_model=StationResponse, status_code=201)
def create_station(
    station: StationCreate,
    db: Session = Depends(get_db)
):
    # Check if station name already exists
    existing = station_crud.get_by_name(db, station.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Station with name '{station.name}' already exists"
        )

    return station_crud.create(db, station)

@router.get("/{station_id}", response_model=StationResponse)
def get_station(
    station_id: int,
    db: Session = Depends(get_db)
):
    station = station_crud.get_by_id(db, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station

@router.get("/", response_model=StationListResponse)
def list_stations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * size
    stations = station_crud.get_all(db, skip=skip, limit=size, search=search)
    total = station_crud.count(db, search=search)

    return StationListResponse(
        stations=stations,
        total=total,
        page=page,
        size=size
    )

@router.put("/{station_id}", response_model=StationResponse)
def update_station(
    station_id: int,
    station_data: StationUpdate,
    db: Session = Depends(get_db)
):
    station = station_crud.update(db, station_id, station_data)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station

@router.delete("/{station_id}", status_code=204)
def delete_station(
    station_id: int,
    db: Session = Depends(get_db)
):
    success = station_crud.delete(db, station_id)
    if not success:
        raise HTTPException(status_code=404, detail="Station not found")
```

**Key Points:**

- Use proper HTTP status codes (201 for creation, 204 for deletion)
- Add validation and error handling
- Include pagination with `Query` parameters
- Use dependency injection for database sessions
- Return appropriate response models

### Step 5: Register API Routes

Add your routes to the main API router:

```python
# back/api/v1/__init__.py
from fastapi import APIRouter
from .stations import router as stations_router

api_router = APIRouter()

api_router.include_router(
    stations_router,
    prefix="/stations",
    tags=["stations"]
)
```

Then ensure the main app includes the API router:

```python
# back/main.py (verify this exists)
from fastapi import FastAPI
from back.api.v1 import api_router

app = FastAPI(title="VeloSim API")

app.include_router(api_router, prefix="/api/v1")
```

### Step 6: Generate and Apply Migration

Create database migration for your new model:

```bash
# Generate migration (ensure your model is imported in alembic/env.py)
alembic revision --autogenerate -m "Add stations table"

# Review the generated migration file
# Check: back/alembic/versions/xxx_add_stations_table.py

# Apply migration
alembic upgrade head
```

**Important**: Make sure to import your model in `back/alembic/env.py`:

```python
# back/alembic/env.py
from back.models import station  # Add this import
```

### Step 7: Test Your Implementation

Test via Swagger UI at http://localhost:8000/api/docs:

1. **POST /api/v1/stations/** - Create a new station
2. **GET /api/v1/stations/** - List all stations
3. **GET /api/v1/stations/{id}** - Get specific station
4. **PUT /api/v1/stations/{id}** - Update station
5. **DELETE /api/v1/stations/{id}** - Delete station

## 🧪 Testing Best Practices

Create comprehensive tests for your feature:

```python
# back/tests/test_stations.py
import pytest
from fastapi.testclient import TestClient
from back.main import app

client = TestClient(app)

def test_create_station():
    response = client.post("/api/v1/stations/", json={
        "name": "Test Station",
        "longitude": -74.006,
        "latitude": 40.7128,
        "capacity": 20
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Station"
    assert data["capacity"] == 20

def test_get_station():
    # Create station first
    create_response = client.post("/api/v1/stations/", json={
        "name": "Get Test Station",
        "longitude": -74.006,
        "latitude": 40.7128
    })
    station_id = create_response.json()["id"]

    # Get station
    response = client.get(f"/api/v1/stations/{station_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test Station"

# Add more tests for update, delete, list, etc.
```

## 📋 Development Checklist

When implementing a new feature, ensure you:

- [ ] **Model**: SQLAlchemy model with proper fields and constraints
- [ ] **Schemas**: Pydantic schemas for create/update/response
- [ ] **CRUD**: Complete database operations with error handling
- [ ] **API**: FastAPI routes with proper status codes and validation
- [ ] **Migration**: Alembic migration generated and applied
- [ ] **Routes**: API router properly registered
- [ ] **Tests**: Comprehensive test coverage
- [ ] **Documentation**: Update relevant README sections
- [ ] **Imports**: All necessary imports in `__init__.py` files

## 🔄 Next Steps

After completing your feature:

1. Run the full test suite: `python -m pytest back/`
2. Check code quality: `black back/ && flake8 back/ && mypy back/`
3. Test via Swagger UI
4. Update documentation
5. Create a pull request

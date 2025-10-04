@echo off
setlocal enabledelayedexpansion

REM Check command argument
if "%1"=="" (
    echo Usage: migrate.bat ^<command^>
    echo.
    echo Available commands:
    echo   init        - Initialize Alembic
    echo   generate    - Generate a new migration
    echo   upgrade     - Apply migrations
    echo   downgrade   - Downgrade migrations
    echo   current     - Show current migration
    echo   history     - Show migration history
    echo   seed        - Seed database with initial data
    echo   help        - Show this help
    exit /b 1
)

set COMMAND=%1

if "%COMMAND%"=="help" (
    echo Available migration commands:
    echo.
    echo   init        - Initialize Alembic configuration
    echo   generate    - Generate a new migration from model changes
    echo   upgrade     - Apply all pending migrations
    echo   downgrade   - Downgrade to previous migration
    echo   current     - Show current migration version
    echo   history     - Show migration history
    echo   seed        - Seed database with initial station data
    echo.
    echo Usage: migrate.bat ^<command^>
    echo Example: migrate.bat upgrade
    exit /b 0
)

if "%COMMAND%"=="generate" (
    if "%2"=="" (
        echo [ERROR] Please provide a migration message
        echo Usage: migrate.bat generate "migration message"
        exit /b 1
    )
    echo [INFO] Generating new migration: %2
    alembic revision --autogenerate -m "%2"
    if errorlevel 1 (
        echo [ERROR] Migration generation failed
        exit /b 1
    )
    echo [SUCCESS] Migration generated successfully
    exit /b 0
)

if "%COMMAND%"=="upgrade" (
    echo [INFO] Running migrations...
    alembic upgrade head
    if errorlevel 1 (
        echo [ERROR] Migration upgrade failed
        exit /b 1
    )
    echo [SUCCESS] Migrations applied successfully
    exit /b 0
)

if "%COMMAND%"=="current" (
    echo [INFO] Checking current migration status...
    alembic current
    exit /b 0
)

if "%COMMAND%"=="status" (
    echo [INFO] Checking current migration status...
    alembic current
    exit /b 0
)

if "%COMMAND%"=="downgrade" (
    echo [INFO] Rolling back last migration...
    alembic downgrade -1
    if errorlevel 1 (
        echo [ERROR] Migration downgrade failed
        exit /b 1
    )
    echo [SUCCESS] Migration rolled back successfully
    exit /b 0
)

if "%COMMAND%"=="history" (
    echo [INFO] Showing migration history...
    alembic history
    exit /b 0
)

if "%COMMAND%"=="init" (
    echo [INFO] Initializing Alembic...
    alembic init alembic
    if errorlevel 1 (
        echo [ERROR] Alembic initialization failed
        exit /b 1
    )
    echo [SUCCESS] Alembic initialized successfully
    exit /b 0
)

if "%COMMAND%"=="seed" (
    echo [INFO] Seeding database with initial data...
    psql -h localhost -p 5433 -U velosim -d velosim -f alembic\seeds\stations.sql -f alembic\seeds\station_tasks.sql
    if errorlevel 1 (
        echo [ERROR] Database seeding failed
        exit /b 1
    )
    echo [SUCCESS] Database seeded successfully
    exit /b 0
)

echo [ERROR] Unknown command: %COMMAND%
echo Use 'migrate.bat help' for available commands
exit /b 1

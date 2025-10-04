@echo off
setlocal enabledelayedexpansion

REM Change to back directory where alembic.ini is located
cd /d "%~dp0..\back"

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
    echo   dropseed    - Drop database, run migrations, and seed data
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
    echo   dropseed    - Drop database, run migrations, and seed data
    echo.
    echo Usage: migrate.bat ^<command^>
    echo Example: migrate.bat upgrade
    exit /b 0
)

if "%COMMAND%"=="generate" (
    if "%2"=="" (
        echo ERROR [velosim.migrate] Please provide a migration message
        echo Usage: migrate.bat generate "migration message"
        exit /b 1
    )
    echo INFO  [velosim.migrate] Generating new migration: %2
    alembic revision --autogenerate -m "%2"
    if errorlevel 1 (
        echo ERROR [velosim.migrate] Migration generation failed
        exit /b 1
    )
    echo INFO  [velosim.migrate] Migration generated successfully
    exit /b 0
)

if "%COMMAND%"=="upgrade" (
    echo INFO  [velosim.migrate] Running migrations...
    alembic upgrade head
    if errorlevel 1 (
        echo ERROR [velosim.migrate] Migration upgrade failed
        exit /b 1
    )
    echo INFO  [velosim.migrate] Migrations applied successfully
    exit /b 0
)

if "%COMMAND%"=="current" (
    echo INFO  [velosim.migrate] Checking current migration status...
    alembic current
    exit /b 0
)

if "%COMMAND%"=="status" (
    echo INFO  [velosim.migrate] Checking current migration status...
    alembic current
    exit /b 0
)

if "%COMMAND%"=="downgrade" (
    echo INFO  [velosim.migrate] Rolling back last migration...
    alembic downgrade -1
    if errorlevel 1 (
        echo ERROR [velosim.migrate] Migration downgrade failed
        exit /b 1
    )
    echo INFO  [velosim.migrate] Migration rolled back successfully
    exit /b 0
)

if "%COMMAND%"=="history" (
    echo INFO  [velosim.migrate] Showing migration history...
    alembic history
    exit /b 0
)

if "%COMMAND%"=="init" (
    echo INFO  [velosim.migrate] Initializing Alembic...
    alembic init alembic
    if errorlevel 1 (
        echo ERROR [velosim.migrate] Alembic initialization failed
        exit /b 1
    )
    echo INFO  [velosim.migrate] Alembic initialized successfully
    exit /b 0
)

if "%COMMAND%"=="seed" (
    echo INFO  [velosim.migrate] Seeding database with initial data...
    python "..\scripts\db_manager.py" seed
    if errorlevel 1 (
        echo ERROR [velosim.migrate] Database seeding failed
        exit /b 1
    )
    echo INFO  [velosim.migrate] Database seeded successfully
    exit /b 0
)

if "%COMMAND%"=="dropseed" (
    echo INFO  [velosim.migrate] Dropping database, running migrations, and seeding...
    python "..\scripts\db_manager.py" dropseed
    if errorlevel 1 (
        echo ERROR [velosim.migrate] Database reset failed
        exit /b 1
    )
    echo INFO  [velosim.migrate] Database reset completed successfully
    exit /b 0
)

echo ERROR [velosim.migrate] Unknown command: %COMMAND%
echo Use 'migrate.bat help' for available commands
exit /b 1

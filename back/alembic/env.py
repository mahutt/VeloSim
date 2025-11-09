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

import os
import sys

from sqlalchemy import create_engine
from alembic import context

# Add the project root to sys.path so we can import our models
current_dir = os.path.dirname(__file__)  # alembic/
back_dir = os.path.dirname(current_dir)  # back/
project_root = os.path.dirname(back_dir)  # project root

sys.path.insert(0, project_root)
sys.path.insert(0, back_dir)

# Import the base from our application
from back.database.session import Base  # noqa: E402

# Import settings for database URL
from back.core.config import settings  # noqa: E402

# Import all models so they are registered with Base.metadata
import back.models  # noqa: F401, E402

# Alembic Config object
config = context.config

# Ensure script_location has a sensible default if alembic.ini is missing or incomplete
if config.get_main_option("script_location") in (None, "", "None"):
    config.set_main_option("script_location", "alembic")

# Resolve database URL: prefer env var, else build from app settings
database_url = (
    os.getenv("DATABASE_URL")
    or getattr(settings, "get_database_url", None)
    or settings.DATABASE_URL
)
if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not set and could not be constructed from settings"
    )

config.set_main_option("sqlalchemy.url", database_url)

# Metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("sqlalchemy.url is not set in alembic config")
    connectable = create_engine(url)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""seed_default_traffic_templates

Revision ID: 45d997a2ee04
Revises: 70e3a53d2e2e
Create Date: 2026-03-25 08:36:41.734978

"""
import tarfile
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45d997a2ee04'
down_revision: Union[str, Sequence[str], None] = '70e3a53d2e2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _read_seed_csv(filename: str) -> str | None:
    """Read traffic template CSV from packaged archive or datasets directory.

    Returns None when no suitable source can be loaded.
    """
    repo_root = Path(__file__).resolve().parents[3]
    datasets_dir = repo_root / "sim" / "traffic" / "traffic_datasets"
    archive_path = datasets_dir / "traffic.tar.gz"

    if archive_path.exists():
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                # Support either bare file names or names nested within folders.
                candidates = [
                    filename,
                    f"./{filename}",
                ]
                for member in tar.getmembers():
                    member_name = Path(member.name).name
                    if member.isfile() and (
                        member.name in candidates or member_name == filename
                    ):
                        extracted = tar.extractfile(member)
                        if extracted is None:
                            continue
                        return extracted.read().decode("utf-8")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to read '{filename}' from archive: {exc}"
            ) from exc

    csv_path = datasets_dir / filename
    if not csv_path.exists():
        fallback = datasets_dir / "traffic.csv"
        if fallback.exists():
            csv_path = fallback
        else:
            return None
    return csv_path.read_text(encoding="utf-8")


def upgrade() -> None:
    """Upgrade schema."""
    seeded_templates = [
        ("default", "default.csv", "Seeded default traffic template"),
        ("high_congestion", "high_congestion.csv", "Seeded high congestion template"),
        (
            "medium_congestion",
            "medium_congestion.csv",
            "Seeded medium congestion template",
        ),
        ("low_congestion", "low_congestion.csv", "Seeded low congestion template"),
    ]

    insert_stmt = sa.text(
        """
        INSERT INTO traffic_templates (key, content, description)
        VALUES (:key, :content, :description)
        ON CONFLICT (key) DO NOTHING
        """
    )

    connection = op.get_bind()
    for key, filename, description in seeded_templates:
        content = _read_seed_csv(filename)
        if content is None:
            raise RuntimeError(
                f"Seed asset '{filename}' not found. Ensure traffic.tar.gz "
                "is present in sim/traffic/traffic_datasets/ or run "
                "'npm run traffic-templates' first."
            )
        connection.execute(
            insert_stmt,
            {
                "key": key,
                "content": content,
                "description": description,
            },
        )


def downgrade() -> None:
    """Downgrade schema."""
    delete_stmt = sa.text(
        """
        DELETE FROM traffic_templates
        WHERE key IN (
            'default', 'high_congestion',
            'medium_congestion', 'low_congestion'
        )
        """
    )
    op.get_bind().execute(delete_stmt)

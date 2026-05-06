"""Pre-beta baseline marker.

This revision is intentionally a no-op. It marks a database that has already
been prepared with the legacy launch bootstrap:

    python backend/run_launch_migrations.py --strict
    python backend/migrate_beta_integrity.py --apply
    alembic -c backend/alembic.ini stamp 0001_prebeta_baseline

Do not use this revision to create a fresh database from zero. The legacy
migrate_*.py scripts remain the pre-Alembic bootstrap, and new schema changes
after this point should be added as Alembic revisions.
"""
from __future__ import annotations


revision = "0001_prebeta_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

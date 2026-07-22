"""Add public access requests reviewed by superadmins."""
from alembic import op
import sqlalchemy as sa


revision = "0018_access_requests"
down_revision = "0017_inventory_defaults"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "access_requests" in set(sa.inspect(bind).get_table_names()):
        return
    op.create_table(
        "access_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_ruc", sa.String(length=11), nullable=False),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("business_address", sa.String(length=500), nullable=True),
        sa.Column("business_phone", sa.String(length=20), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("public_token_hash", sa.String(length=64), nullable=False),
        sa.Column("pending_email_key", sa.String(length=255), nullable=True),
        sa.Column("pending_ruc_key", sa.String(length=11), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_token_hash", name="uq_access_requests_public_token"),
        sa.UniqueConstraint("pending_email_key", name="uq_access_requests_pending_email"),
        sa.UniqueConstraint("pending_ruc_key", name="uq_access_requests_pending_ruc"),
    )
    op.create_index("ix_access_requests_email", "access_requests", ["email"])
    op.create_index(
        "ix_access_requests_status_created",
        "access_requests",
        ["status", "created_at"],
    )
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE access_requests ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            DO $$
            DECLARE
                sequence_name text;
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE access_requests FROM anon';
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE access_requests FROM authenticated';
                END IF;

                sequence_name := pg_get_serial_sequence('access_requests', 'id');
                IF sequence_name IS NOT NULL THEN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        EXECUTE format('REVOKE ALL PRIVILEGES ON SEQUENCE %s FROM anon', sequence_name);
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        EXECUTE format('REVOKE ALL PRIVILEGES ON SEQUENCE %s FROM authenticated', sequence_name);
                    END IF;
                END IF;
            END
            $$;
            """
        )


def downgrade():
    op.drop_index("ix_access_requests_status_created", table_name="access_requests")
    op.drop_index("ix_access_requests_email", table_name="access_requests")
    op.drop_table("access_requests")

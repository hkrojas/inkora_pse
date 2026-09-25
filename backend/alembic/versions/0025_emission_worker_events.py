"""Add compatible worker leases and transactional, payload-free wake signals."""
from alembic import op
import sqlalchemy as sa

revision = "0025_emission_worker_events"
down_revision = "0024_internal_transfer_gre"
branch_labels = None
depends_on = None

NOTIFY_FUNCTION = """
CREATE OR REPLACE FUNCTION public.inkora_notify_emission_jobs() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.status IN ('queued', 'retry') THEN
      PERFORM pg_notify('inkora_emission_jobs_changed', '');
    END IF;
  ELSIF (NEW.status IN ('queued', 'retry') AND
       (OLD.status IS DISTINCT FROM NEW.status OR
        OLD.available_at IS DISTINCT FROM NEW.available_at OR
        OLD.priority IS DISTINCT FROM NEW.priority))
       OR (OLD.status = 'processing' AND NEW.status <> 'processing') THEN
    PERFORM pg_notify('inkora_emission_jobs_changed', '');
  END IF;
  RETURN NEW;
END $$
"""


def upgrade():
    for name, kind in [
        ('worker_owner', sa.String(128)), ('lease_token', sa.String(36)),
        ('lease_expires_at', sa.DateTime()), ('execution_started_at', sa.DateTime()),
    ]:
        op.add_column('document_emission_jobs', sa.Column(name, kind, nullable=True))
    op.add_column('document_emission_attempts', sa.Column('lease_token', sa.String(36), nullable=True))
    op.add_column('document_emission_attempts', sa.Column('late_result_snapshot', sa.JSON(), nullable=True))
    op.create_index('ix_emission_processing_tenant', 'document_emission_jobs', ['tenant_id'],
                    postgresql_where=sa.text("status = 'processing'"))
    op.create_index('ix_emission_processing_lease', 'document_emission_jobs', ['lease_expires_at'],
                    postgresql_where=sa.text("status = 'processing'"))
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(NOTIFY_FUNCTION)
        op.execute("""CREATE TRIGGER inkora_emission_jobs_changed
            AFTER INSERT OR UPDATE OF status, available_at, priority
            ON document_emission_jobs FOR EACH ROW
            EXECUTE FUNCTION public.inkora_notify_emission_jobs()""")


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER IF EXISTS inkora_emission_jobs_changed ON document_emission_jobs')
        op.execute('DROP FUNCTION IF EXISTS public.inkora_notify_emission_jobs()')
    op.drop_index('ix_emission_processing_lease', table_name='document_emission_jobs')
    op.drop_index('ix_emission_processing_tenant', table_name='document_emission_jobs')
    for name in ['late_result_snapshot', 'lease_token']:
        op.drop_column('document_emission_attempts', name)
    for name in ['execution_started_at', 'lease_expires_at', 'lease_token', 'worker_owner']:
        op.drop_column('document_emission_jobs', name)

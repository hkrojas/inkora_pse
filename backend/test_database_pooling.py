from database import _database_url_uses_transaction_pooler


def test_detects_supabase_transaction_pooler_by_port():
    assert _database_url_uses_transaction_pooler(
        "postgresql://app:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )


def test_detects_pgbouncer_flag_on_database_url():
    assert _database_url_uses_transaction_pooler(
        "postgresql://app:secret@db.example.supabase.co:5432/postgres?pgbouncer=true"
    )


def test_direct_supabase_database_url_is_not_transaction_pooler():
    assert not _database_url_uses_transaction_pooler(
        "postgresql://app:secret@db.example.supabase.co:5432/postgres?sslmode=require"
    )

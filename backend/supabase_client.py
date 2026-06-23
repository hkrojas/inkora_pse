from supabase import Client, create_client

from config import settings

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.has_supabase_storage:
        raise RuntimeError(
            "Supabase Storage no esta configurado. Defina SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY."
        )

    # Server-side storage operations must use the secret/service key. The
    # publishable key is kept only as a local-development fallback.
    storage_key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    if settings.is_non_local and not storage_key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY es obligatoria para Storage en staging/produccion."
        )
    storage_key = storage_key or settings.SUPABASE_KEY
    _supabase_client = create_client(settings.SUPABASE_URL, storage_key)
    return _supabase_client

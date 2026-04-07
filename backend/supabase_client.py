from supabase import Client, create_client

from config import settings

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.has_supabase_storage:
        raise RuntimeError(
            "Supabase Storage no esta configurado. Defina SUPABASE_URL y SUPABASE_KEY."
        )

    _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client

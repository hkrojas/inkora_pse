from supabase import create_client, Client
from config import settings

# Cliente global de Supabase
# Se utiliza el Service Role Key si se requiere bypass de RLS para administración,
# pero para el Storage con las claves de Settings es suficiente.
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

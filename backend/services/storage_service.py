from supabase_client import supabase

async def upload_to_storage(file_bytes: bytes, folder_name: str, filename: str, content_type: str):
    """
    Sube un archivo al bucket 'printflow-archivos' y retorna la URL pública.
    """
    path = f"{folder_name}/{filename}"
    
    # Subir el archivo
    # Se usa x-upsert: true para permitir actualizaciones si el nombre coincide.
    res = supabase.storage.from_("printflow-archivos").upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type, "x-upsert": "true"}
    )
    
    # Obtener URL pública absoluta
    public_url = supabase.storage.from_("printflow-archivos").get_public_url(path)
    return public_url

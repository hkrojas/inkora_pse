# backend/init_db.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
import models

def init_db():
    print("Iniciando creación de tablas en Supabase...")
    try:
        models.Base.metadata.create_all(bind=engine)
        print("[OK] Tablas creadas exitosamente.")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar a la base de datos: {e}")
        print("Asegúrate de haber configurado tu DATABASE_URL en el archivo .env con la contraseña correcta.")

if __name__ == "__main__":
    init_db()

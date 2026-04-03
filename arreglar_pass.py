import sys
# Intentamos importar las librerías necesarias
try:
    from sqlalchemy import create_engine, text
    from passlib.context import CryptContext
except ImportError as e:
    print("❌ Falta una librería. Ejecuta en tu terminal:")
    print("pip install sqlalchemy psycopg2-binary passlib bcrypt")
    sys.exit(1)

# --- CONFIGURACIÓN LISTA ---
# Neon (Backup): # DATABASE_URL = "postgresql://neondb_owner:npg_7IFj5eHxlnLC@ep-bold-term-ad5m4ir1-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
# Supabase Printflow-db (IPv4 Pooler):
DATABASE_URL = "postgresql://postgres.qbobhyjycmvhkocxnfhc:BcHyLIvvwCU7N0iZ@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"

# Datos del usuario a recuperar
EMAIL_USUARIO = "corporacionaquinobp@gmail.com"
NUEVA_CLAVE = "Aquino2026" 
# ---------------------------

def arreglar_password():
    print(f"🔒 Generando hash para la contraseña: '{NUEVA_CLAVE}'...")
    
    # 1. Crear el hash seguro
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    nuevo_hash = pwd_context.hash(NUEVA_CLAVE)
    
    print(f"🌍 Conectando a Neon para el usuario {EMAIL_USUARIO}...")
    
    # 2. Conexión y actualización
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # Verificamos si el usuario existe
            check_query = text("SELECT id, email, is_active FROM users WHERE email = :email")
            user = connection.execute(check_query, {"email": EMAIL_USUARIO}).fetchone()
            
            if not user:
                print(f"❌ ERROR: No se encontró ningún usuario con el correo '{EMAIL_USUARIO}'.")
                return

            # Ejecutamos la actualización
            update_query = text("""
                UPDATE users 
                SET hashed_password = :password
                WHERE email = :email
            """)
            
            connection.execute(update_query, {"password": nuevo_hash, "email": EMAIL_USUARIO})
            connection.commit()
            
            print(f"✅ ¡ÉXITO! La contraseña de {EMAIL_USUARIO} ha sido restablecida.")
            print(f"➡️  Ahora puede iniciar sesión con: {NUEVA_CLAVE}")

    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    arreglar_password()
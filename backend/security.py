from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

# Importaciones locales
import models
from config import settings

# Configuración de hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de autenticación (Token en Header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ==========================================
# FUNCIONES DE HASHING (Password)
# ==========================================

def verify_password(plain_password, hashed_password):
    """Verifica si la contraseña plana coincide con el hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)

# ==========================================
# FUNCIONES DE TOKEN (JWT)
# ==========================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT firmado."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Asegúrate de tener SECRET_KEY y ALGORITHM en tu config.py o .env
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_access_token_with_claims(user, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT con claims adicionales para evitar queries a la BD."""
    to_encode = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "is_superadmin": user.is_superadmin,
        "rol": user.rol
    }
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# ==========================================
# FUNCIONES DE AUTENTICACIÓN (LOGIN)
# ==========================================

def get_user_by_email(db: Session, email: str):
    """Busca un usuario por email en la BD (Helper interno)."""
    return db.query(models.User).options(joinedload(models.User.tenant)).filter(models.User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    """Verifica usuario y contraseña. Retorna el usuario si es válido, False si no."""
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# ==========================================
# DEPENDENCIA DE USUARIO ACTUAL
# ==========================================

def get_current_user(db: Session, token: str):
    """
    Decodifica el token y recupera el objeto User actual.
    Usado por @app.get("/users/me") y rutas protegidas.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    
    return user

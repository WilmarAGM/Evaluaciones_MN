import os
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models

# En producción, define JWT_SECRET_KEY en el entorno. Si no está presente
# (prototipo local), se genera una clave aleatoria al arrancar el proceso:
# esto invalida tokens viejos en cada reinicio, pero evita un secreto fijo en el código.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# Sesión única por estudiante: una cuenta con actividad en los últimos
# SESSION_IDLE_MINUTES bloquea nuevos inicios de sesión desde otro navegador.
SESSION_IDLE_MINUTES = 10
# last_seen se refresca como máximo cada tantos segundos, para no escribir en
# la base de datos en cada petición.
LAST_SEEN_REFRESH_SECONDS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def has_active_session(student: models.Student) -> bool:
    """True si el estudiante tiene una sesión abierta con actividad reciente."""
    if not student.session_id or student.last_seen is None:
        return False
    return _utcnow() - _aware(student.last_seen) < timedelta(minutes=SESSION_IDLE_MINUTES)


def start_session(db: Session, student: models.Student, device_id: str | None) -> str:
    """Abre una sesión nueva (reemplaza la anterior si la hubiera) y devuelve
    su identificador, que va como claim `sid` dentro del JWT."""
    student.session_id = secrets.token_hex(16)
    student.device_id = device_id
    student.last_seen = _utcnow()
    db.commit()
    return student.session_id


def get_current_student(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Student:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    student = db.query(models.Student).filter(models.Student.email == email).first()
    if student is None:
        raise credentials_exception

    # Sesión única: solo aplica a estudiantes. El token debe corresponder a la
    # sesión vigente; si el estudiante salió, o el docente la liberó y se abrió
    # otra, este token deja de valer.
    if student.role == "student":
        if payload.get("sid") is None or payload.get("sid") != student.session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tu sesión ya no es válida. Inicia sesión de nuevo.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if student.last_seen is None or (
            _utcnow() - _aware(student.last_seen) > timedelta(seconds=LAST_SEEN_REFRESH_SECONDS)
        ):
            student.last_seen = _utcnow()
            db.commit()
    return student


def get_current_teacher(student: models.Student = Depends(get_current_student)) -> models.Student:
    if student.role != "teacher":
        raise HTTPException(status_code=403, detail="Acceso solo para docentes")
    return student


def get_current_admin(student: models.Student = Depends(get_current_student)) -> models.Student:
    if student.role != "admin":
        raise HTTPException(status_code=403, detail="Acceso solo para administradores")
    return student


def get_current_teacher_or_admin(student: models.Student = Depends(get_current_student)) -> models.Student:
    """Para endpoints compartidos entre ambos roles (p. ej. el sondeo del
    job de carga de .tex con IA, que arranca tanto un docente como el admin
    sobre su propio banco)."""
    if student.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Acceso solo para docentes o administradores")
    return student

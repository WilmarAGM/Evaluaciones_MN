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
    return student


def get_current_teacher(student: models.Student = Depends(get_current_student)) -> models.Student:
    if student.role != "teacher":
        raise HTTPException(status_code=403, detail="Acceso solo para docentes")
    return student


def get_current_admin(student: models.Student = Depends(get_current_student)) -> models.Student:
    if student.role != "admin":
        raise HTTPException(status_code=403, detail="Acceso solo para administradores")
    return student

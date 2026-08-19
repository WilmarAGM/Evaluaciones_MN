"""Crea la cuenta admin (una sola, dueña del panel /admin/teachers). Uso: python -m app.seed

No toca el rol si la cuenta ya existe: tras la migración a grupos (ver
migrate_groups.py) esta cuenta pasa a role="admin" y debe quedarse así en
cada reinicio, no volver a "teacher"."""
from .database import SessionLocal, engine, Base
from . import models
from .security import hash_password

ADMIN_EMAIL = "wagonzalezm@unal.edu.co"
ADMIN_DOCUMENTO = "1038359871"
ADMIN_NAME = "Wilmar A. Gonzalez M."


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        student = db.query(models.Student).filter_by(email=ADMIN_EMAIL).first()
        if not student:
            student = models.Student(
                email=ADMIN_EMAIL,
                documento=ADMIN_DOCUMENTO,
                hashed_password=hash_password(ADMIN_DOCUMENTO),
                full_name=ADMIN_NAME,
                role="admin",
            )
            db.add(student)
            db.commit()
            print("Admin creado:", student.email)
        else:
            print(f"Cuenta ya existía (rol={student.role}):", student.email)
    finally:
        db.close()


if __name__ == "__main__":
    seed()

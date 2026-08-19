"""Crea (o promueve) la cuenta docente. Uso: python -m app.seed"""
from .database import SessionLocal, engine, Base
from . import models
from .security import hash_password

TEACHER_EMAIL = "wagonzalezm@unal.edu.co"
TEACHER_DOCUMENTO = "1038359871"
TEACHER_NAME = "Wilmar A. Gonzalez M."


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        student = db.query(models.Student).filter_by(email=TEACHER_EMAIL).first()
        if not student:
            student = models.Student(
                email=TEACHER_EMAIL,
                documento=TEACHER_DOCUMENTO,
                hashed_password=hash_password(TEACHER_DOCUMENTO),
                full_name=TEACHER_NAME,
                role="teacher",
            )
            db.add(student)
            db.commit()
            print("Docente creado:", student.email)
        elif student.role != "teacher":
            student.role = "teacher"
            db.commit()
            print("Docente actualizado (rol=teacher):", student.email)
        else:
            print("Docente ya existía:", student.email)
    finally:
        db.close()


if __name__ == "__main__":
    seed()

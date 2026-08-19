"""Importa estudiantes desde LMN.xls (columnas: APELLIDOS Y NOMBRE, DOCUMENTO, CORREO)
a la base de datos. La contraseña inicial de cada estudiante es su documento.

Uso: python -m app.import_students
"""
import os

import xlrd

from .database import SessionLocal, engine, Base
from . import models
from .security import hash_password

XLS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "LMN.xls")


def _normalize_name(raw: str) -> str:
    return " ".join(part.capitalize() for part in raw.strip().split())


def import_students(xls_path: str = XLS_PATH):
    Base.metadata.create_all(bind=engine)
    wb = xlrd.open_workbook(xls_path)
    sheet = wb.sheet_by_index(0)

    created, skipped = 0, 0
    db = SessionLocal()
    try:
        for row_idx in range(1, sheet.nrows):
            full_name_raw = str(sheet.cell_value(row_idx, 0)).strip()
            correo = str(sheet.cell_value(row_idx, 2)).strip()
            if not correo:
                continue

            doc_value = sheet.cell_value(row_idx, 1)
            if isinstance(doc_value, float):
                documento = str(int(doc_value)) if doc_value.is_integer() else str(doc_value)
            else:
                documento = str(doc_value).strip()

            existing = db.query(models.Student).filter_by(email=correo).first()
            if existing:
                skipped += 1
                continue

            student = models.Student(
                email=correo,
                documento=documento,
                hashed_password=hash_password(documento),
                full_name=_normalize_name(full_name_raw),
                role="student",
            )
            db.add(student)
            created += 1

        db.commit()
    finally:
        db.close()

    print(f"Estudiantes creados: {created}. Ya existían (omitidos): {skipped}.")


if __name__ == "__main__":
    import_students()

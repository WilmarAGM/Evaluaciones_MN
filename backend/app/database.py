import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./evaluaciones.db")

# El pool por defecto de SQLAlchemy (5 conexiones + 10 de desborde = 15) se
# queda corto: cada request mantiene la conexión abierta durante toda la
# ejecución del código del estudiante (varios segundos), así que con más de
# 15 estudiantes ejecutando código a la vez, el resto queda en fila y termina
# fallando con "QueuePool limit ... connection timed out". Lo subimos bastante
# ya que SQLite no tiene el mismo costo por conexión que otras bases de datos.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=100,
    max_overflow=100,
    pool_timeout=30,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    # WAL permite que lecturas y escrituras concurrentes no se bloqueen entre
    # sí tan agresivamente como el modo por defecto de SQLite.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

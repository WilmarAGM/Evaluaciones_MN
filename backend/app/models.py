import json

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    Float,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    documento = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="student", nullable=False)  # "student" | "teacher" | "admin"

    # Sección del curso (1-4). Para un estudiante: su grupo. Para un docente:
    # el grupo que dicta (aísla qué exámenes/bancos/estudiantes ve). None
    # para "admin", que no dicta ningún grupo.
    group = Column(Integer, nullable=True)

    submissions = relationship("Submission", back_populates="student")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=50, nullable=True)  # None = sin límite de tiempo
    is_open = Column(Boolean, default=True, nullable=False)  # el docente habilita/deshabilita el acceso
    group = Column(Integer, nullable=True)  # grupo dueño del examen (1-4)

    exam_problems = relationship(
        "ExamProblem", back_populates="exam", order_by="ExamProblem.order",
        cascade="all, delete-orphan",
    )
    slots = relationship(
        "ExamSlot", back_populates="exam", order_by="ExamSlot.order",
        cascade="all, delete-orphan",
    )

    @property
    def problems(self):
        """Lista de Problem en el orden de este examen, vía la tabla puente
        ExamProblem. No usar para serializar el `order` por examen (ver
        ExamProblem.order para eso) — el Problem en sí no sabe su posición,
        ya que un mismo problema puede pertenecer a varios exámenes."""
        return [ep.problem for ep in self.exam_problems]


class ProblemBank(Base):
    __tablename__ = "problem_banks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    group = Column(Integer, nullable=True)  # grupo dueño del banco (1-4)

    problems = relationship("Problem", back_populates="bank")


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("problem_banks.id"), nullable=False)
    title = Column(String, nullable=False)
    statement_md = Column(Text, nullable=False)
    starter_code = Column(Text, nullable=False)
    solution_code = Column(Text, nullable=True)

    # "draft" = generado (p.ej. por el pipeline de agentes IA) pendiente de
    # revisión del docente; nunca se ofrece a estudiantes (ni como fijo ni
    # como candidato de sorteo en un slot "random") hasta pasar a "published".
    status = Column(String, default="published", nullable=False)

    # Notas de auditoría del pipeline de agentes IA (chequeo numérico contra
    # la respuesta de referencia del .tex original + auditoría cualitativa
    # del agente 4, ver gemini_agents.py). None para problemas sin auditar
    # (creados a mano o antes de que existiera esta auditoría).
    review_notes = Column(Text, nullable=True)

    # Rúbrica genérica: lista JSON de checks, cada uno de tipo "call" (llamar
    # una rutina, opcionalmente validando argumentos/función pasada), "function"
    # (definir una función/lambda que coincide numéricamente con una referencia)
    # o "final_value" (una variable final con el valor numérico esperado).
    # Ver app/executor.py para el detalle de cada tipo.
    rubric = Column(Text, default="[]")

    bank = relationship("ProblemBank", back_populates="problems")
    exam_problems = relationship("ExamProblem", back_populates="problem")

    @property
    def max_score(self):
        return sum(c["points"] for c in json.loads(self.rubric or "[]"))


class ExamProblem(Base):
    """Tabla puente: qué problemas (de qué bancos) componen un examen concreto,
    y en qué orden. Un mismo Problem puede reutilizarse en varios exámenes."""

    __tablename__ = "exam_problems"
    __table_args__ = (UniqueConstraint("exam_id", "problem_id", name="uq_exam_problem"),)

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    order = Column(Integer, default=0)

    exam = relationship("Exam", back_populates="exam_problems")
    problem = relationship("Problem", back_populates="exam_problems")


class ExamSlot(Base):
    """Un 'puesto' dentro de la composición de un examen creado desde el
    panel docente: o un problema fijo, o N problemas sorteados de un banco
    (sorteo hecho una vez por estudiante, ver AttemptProblem). Los exámenes
    legados (creados a mano por script) no usan slots — siguen resolviendo
    su lista de problemas vía ExamProblem, igual que siempre."""

    __tablename__ = "exam_slots"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    order = Column(Integer, default=0)
    kind = Column(String, nullable=False)  # "fixed" | "random"
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)  # solo si kind == "fixed"
    bank_id = Column(Integer, ForeignKey("problem_banks.id"), nullable=True)  # solo si kind == "random"
    count = Column(Integer, default=1)  # solo si kind == "random"

    exam = relationship("Exam", back_populates="slots")
    problem = relationship("Problem")
    bank = relationship("ProblemBank")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"
    __table_args__ = (UniqueConstraint("student_id", "exam_id", name="uq_attempt_student_exam"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    duration_seconds = Column(Integer, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    student = relationship("Student")
    exam = relationship("Exam")
    assigned_problems = relationship(
        "AttemptProblem", back_populates="attempt", order_by="AttemptProblem.order",
        cascade="all, delete-orphan",
    )


class AttemptProblem(Base):
    """Asignación concreta y congelada de qué Problem le tocó a un
    estudiante en un ExamSlot — se resuelve (sorteando si el slot es
    aleatorio) la primera vez que el estudiante abre el examen, y no cambia
    después, para que pueda salir y volver a entrar sin perder ni repetir
    el sorteo."""

    __tablename__ = "attempt_problems"
    __table_args__ = (UniqueConstraint("attempt_id", "slot_id", name="uq_attempt_slot"),)

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("exam_slots.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    order = Column(Integer, default=0)

    attempt = relationship("ExamAttempt", back_populates="assigned_problems")
    problem = relationship("Problem")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("student_id", "problem_id", name="uq_submission_student_problem"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    code = Column(Text, nullable=False)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)

    total_score = Column(Float, default=0.0)
    checks_report = Column(Text, default="[]")  # JSON: [{label, passed, points, max_points}, ...]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    student = relationship("Student", back_populates="submissions")
    problem = relationship("Problem")

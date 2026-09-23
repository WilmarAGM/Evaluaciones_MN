from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    email: str
    password: str
    # Identificador aleatorio guardado en el navegador; permite que un
    # estudiante recupere su propia sesión (p. ej. cerró la pestaña) sin
    # esperar a que venza la inactividad. Ver security.start_session.
    device_id: Optional[str] = None


class RegisterRequest(BaseModel):
    email: str
    documento: str
    full_name: Optional[str] = None
    group: int = Field(ge=1, le=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    full_name: Optional[str] = None
    email: str
    role: str = "student"
    group: Optional[int] = None


class ProblemOut(BaseModel):
    id: int
    order: int
    title: str
    statement_md: str
    starter_code: str
    max_score: float

    class Config:
        from_attributes = True


class ExamOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None  # None = sin límite de tiempo
    max_violations: int = 0  # 0 = sin control de salidas de ventana
    problems: list[ProblemOut]

    class Config:
        from_attributes = True


class ExamListOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: str  # "not_started" | "in_progress" | "finished"
    is_open: bool = True

    class Config:
        from_attributes = True


class AttemptOut(BaseModel):
    started_at: datetime
    duration_seconds: Optional[int] = None
    remaining_seconds: Optional[int] = None
    finished: bool
    violations: int = 0
    max_violations: int = 0
    annulled: bool = False
    annul_reason: Optional[str] = None


class ViolationIn(BaseModel):
    kind: str  # "hidden" | "blur" | "fullscreen_exit"


class RunRequest(BaseModel):
    code: str


class RunResult(BaseModel):
    stdout: str
    stderr: str
    checks: list = []
    total_score: float = 0.0
    max_score: float = 0.0
    solution_code: Optional[str] = None
    figures: list[str] = []  # PNGs en base64 (sin el prefijo data:image/...), una por figura de matplotlib


class SaveResult(BaseModel):
    saved: bool
    saved_at: datetime


class MySubmissionOut(BaseModel):
    problem_id: int
    code: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    saved_at: datetime

    class Config:
        from_attributes = True


class ProblemResultOut(BaseModel):
    problem_id: int
    title: str
    max_score: float
    score: float
    checks: list
    code: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class ExamResultsOut(BaseModel):
    exam_title: str
    total_score: float
    max_score: float
    problems: list[ProblemResultOut]
    annulled: bool = False
    annul_reason: Optional[str] = None
    violations: int = 0


# ---- Vistas de docente ----


class TeacherExamListOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_open: bool = True
    max_violations: int = 0
    total_students: int
    not_started: int
    in_progress: int
    finished: int
    avg_score: float
    max_score: float


class TeacherToggleOpenOut(BaseModel):
    exam_id: int
    is_open: bool


class CriterionStatOut(BaseModel):
    label: str
    max_points: float
    pass_rate: float  # % de estudiantes (con intento) que obtuvieron los puntos completos


class ProblemStatOut(BaseModel):
    problem_id: int
    title: str
    max_score: float
    avg_score: float
    criteria: list[CriterionStatOut]


class ScoreBucketOut(BaseModel):
    label: str
    count: int


class StudentRowOut(BaseModel):
    student_id: int
    full_name: Optional[str] = None
    email: str
    documento: str
    status: str  # not_started | in_progress | finished
    total_score: float
    max_score: float
    nota_5: float
    problem_scores: list[float]
    annulled: bool = False
    violations: int = 0


class BankProblemOut(BaseModel):
    id: int
    title: str
    max_score: float
    status: str = "published"  # "draft" | "published"
    review_notes: Optional[str] = None


class BankOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    problems: list[BankProblemOut]


class TeacherCreateBankIn(BaseModel):
    title: str
    description: Optional[str] = None


class LoadTexCreatedOut(BaseModel):
    id: int
    title: str
    max_score: float
    review_notes: Optional[str] = None


class LoadTexSkippedOut(BaseModel):
    title: str
    reason: str


class LoadTexResultOut(BaseModel):
    bank_id: int
    created: list[LoadTexCreatedOut]
    skipped: list[LoadTexSkippedOut]
    calls_today: int
    tokens_today: int


class TeacherProblemDetailOut(BaseModel):
    id: int
    bank_id: int
    bank_title: str
    title: str
    statement_md: str
    starter_code: str
    solution_code: Optional[str] = None
    rubric: list  # checks crudos (label/type/points/... según el tipo, ver executor.py)
    max_score: float
    status: str
    review_notes: Optional[str] = None


class ExamSlotIn(BaseModel):
    kind: str  # "fixed" | "random"
    problem_id: Optional[int] = None  # requerido si kind == "fixed"
    bank_id: Optional[int] = None  # requerido si kind == "random"
    count: int = 1  # solo usado si kind == "random"


class TeacherCreateExamIn(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None  # None = sin límite
    max_violations: int = Field(default=0, ge=0, le=20)  # 0 = sin control de salidas de ventana
    slots: list[ExamSlotIn]


class TeacherExamDashboardOut(BaseModel):
    exam_id: int
    exam_title: str
    total_students: int
    not_started: int
    in_progress: int
    finished: int
    avg_score: float
    avg_nota_5: float
    max_score: float
    score_distribution: list[ScoreBucketOut]
    problems: list[ProblemStatOut]
    students: list[StudentRowOut]


# ---- Vistas de admin ----


class AdminTeacherIn(BaseModel):
    email: str
    full_name: str
    group: int = Field(ge=1, le=4)


class AdminGroupStudentsOut(BaseModel):
    group: int
    count: int


class AdminTeacherOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    group: Optional[int] = None

    class Config:
        from_attributes = True


# ---- Roster de estudiantes (docente) ----


class AddStudentIn(BaseModel):
    full_name: str
    documento: str
    email: str


class StudentRosterOut(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str
    documento: str
    session_active: bool = False  # tiene una sesión abierta con actividad reciente

    class Config:
        from_attributes = True


class RosterRejectedRowOut(BaseModel):
    row: int
    motivo: str


class ImportRosterResultOut(BaseModel):
    created: int
    skipped: int
    rejected: list[RosterRejectedRowOut]


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

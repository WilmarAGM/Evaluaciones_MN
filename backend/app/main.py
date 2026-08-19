import io
import json
import os
import random
import tempfile
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session

from . import models, schemas, executor
from .database import get_db, Base, engine
from .gemini_agents import orchestrate_load_tex
from .gemini_quota import QuotaExceededError, get_usage_today
from .import_students import _normalize_name
from .security import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_student,
    get_current_teacher,
    get_current_admin,
)

ALLOWED_EMAIL_DOMAIN = "@unal.edu.co"

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Evaluaciones Métodos Numéricos - Local")

# Orígenes de desarrollo local siempre permitidos; el/los del frontend en
# producción (ej. Vercel) se agregan vía CORS_ORIGINS (separados por coma),
# ya que la URL final no se conoce hasta desplegar el proyecto en Vercel.
_extra_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *_extra_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now():
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_or_create_attempt(db: Session, student: models.Student, exam: models.Exam) -> models.ExamAttempt:
    attempt = (
        db.query(models.ExamAttempt)
        .filter(models.ExamAttempt.student_id == student.id, models.ExamAttempt.exam_id == exam.id)
        .first()
    )
    if not attempt:
        # duration_seconds no se usa cuando exam.duration_minutes es None (examen sin
        # límite de tiempo), pero la columna es NOT NULL, así que igual guardamos un
        # valor coherente por si el examen luego se reconfigura con un límite.
        attempt = models.ExamAttempt(
            student_id=student.id,
            exam_id=exam.id,
            duration_seconds=(exam.duration_minutes or 0) * 60,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    return attempt


def attempt_status(attempt: models.ExamAttempt, db: Session) -> dict:
    started_at = _aware(attempt.started_at)

    if attempt.exam.duration_minutes is None:
        finished = attempt.finished_at is not None
        return {"started_at": started_at, "duration_seconds": None, "remaining_seconds": None, "finished": finished}

    deadline = started_at + timedelta(seconds=attempt.duration_seconds)
    remaining = int((deadline - now()).total_seconds())

    if remaining <= 0 and attempt.finished_at is None:
        attempt.finished_at = deadline
        db.commit()
        _regrade_attempt(db, attempt.student, attempt.exam)

    remaining = max(0, remaining)
    finished = attempt.finished_at is not None
    return {"started_at": started_at, "duration_seconds": attempt.duration_seconds, "remaining_seconds": remaining, "finished": finished}


def require_active_attempt(db: Session, student: models.Student, exam: models.Exam) -> models.ExamAttempt:
    attempt = get_or_create_attempt(db, student, exam)
    status = attempt_status(attempt, db)
    if status["finished"]:
        raise HTTPException(status_code=403, detail="El tiempo del examen ha finalizado.")
    return attempt


def run_problem_code(code: str, problem: models.Problem) -> dict:
    return executor.run_student_code(code, json.loads(problem.rubric or "[]"))


def get_problem_or_404(db: Session, problem_id: int) -> models.Problem:
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problema no encontrado")
    return problem


def get_teacher_problem_or_404(db: Session, problem_id: int, group: int) -> models.Problem:
    """Como get_problem_or_404, pero exige que el problema pertenezca a un
    banco del grupo del docente (Problem no tiene columna group propia,
    hereda el aislamiento vía su banco)."""
    problem = (
        db.query(models.Problem)
        .join(models.ProblemBank, models.Problem.bank_id == models.ProblemBank.id)
        .filter(models.Problem.id == problem_id, models.ProblemBank.group == group)
        .first()
    )
    if not problem:
        raise HTTPException(status_code=404, detail="Problema no encontrado")
    return problem


def get_problem_usage_blockers(db: Session, problem_id: int) -> list[str]:
    """Razones por las que este problema NO se puede borrar sin riesgo de
    romper un examen existente o perder datos de estudiantes. Lista vacía =
    se puede borrar sin problema."""
    blockers = []

    fixed_slots = (
        db.query(models.ExamSlot)
        .filter(models.ExamSlot.kind == "fixed", models.ExamSlot.problem_id == problem_id)
        .all()
    )
    for slot in fixed_slots:
        blockers.append(f"es un ejercicio fijo del examen '{slot.exam.title}'")

    exam_problems = db.query(models.ExamProblem).filter(models.ExamProblem.problem_id == problem_id).all()
    for ep in exam_problems:
        blockers.append(f"forma parte de la lista de problemas del examen '{ep.exam.title}'")

    if db.query(models.AttemptProblem).filter(models.AttemptProblem.problem_id == problem_id).first():
        blockers.append("ya fue asignado (sorteado) a intentos de estudiantes")

    if db.query(models.Submission).filter(models.Submission.problem_id == problem_id).first():
        blockers.append("tiene entregas de estudiantes guardadas")

    return blockers


def get_bank_or_404(db: Session, bank_id: int, group: int | None = None) -> models.ProblemBank:
    q = db.query(models.ProblemBank).filter(models.ProblemBank.id == bank_id)
    if group is not None:
        q = q.filter(models.ProblemBank.group == group)
    bank = q.first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
    return bank


def get_exam_or_404(db: Session, exam_id: int, group: int | None = None) -> models.Exam:
    q = db.query(models.Exam).filter(models.Exam.id == exam_id)
    if group is not None:
        q = q.filter(models.Exam.group == group)
    exam = q.first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado")
    return exam


def get_exam_for_student_problem(db: Session, student: models.Student, problem: models.Problem) -> models.Exam:
    """Resuelve a qué examen pertenece `problem` para efectos de validar el
    intento activo del estudiante. Primero revisa si le fue asignado vía
    sorteo por estudiante (AttemptProblem, ver resolve_exam_problems); si
    no, cae al caso legado: un mismo Problem (banco) puede estar asignado a
    varios exámenes vía ExamProblem, si el estudiante ya tiene un intento en
    curso en alguno de ellos se usa ese, si no se usa el único candidato
    (caso normal: el problema solo está en un examen activo)."""
    assigned = (
        db.query(models.AttemptProblem)
        .join(models.ExamAttempt, models.AttemptProblem.attempt_id == models.ExamAttempt.id)
        .filter(
            models.AttemptProblem.problem_id == problem.id,
            models.ExamAttempt.student_id == student.id,
        )
        .first()
    )
    if assigned:
        return get_exam_or_404(db, assigned.attempt.exam_id, group=student.group)

    exam_ids = [ep.exam_id for ep in problem.exam_problems]
    if not exam_ids:
        raise HTTPException(status_code=404, detail="Este problema no está asignado a ningún examen")
    if len(exam_ids) == 1:
        return get_exam_or_404(db, exam_ids[0], group=student.group)

    attempt = (
        db.query(models.ExamAttempt)
        .filter(models.ExamAttempt.student_id == student.id, models.ExamAttempt.exam_id.in_(exam_ids))
        .first()
    )
    if attempt:
        return get_exam_or_404(db, attempt.exam_id, group=student.group)
    raise HTTPException(
        status_code=409,
        detail="Este problema pertenece a varios exámenes y no tienes un intento activo en ninguno.",
    )


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.email == payload.email).first()
    if not student or not verify_password(payload.password, student.hashed_password):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    token = create_access_token({"sub": student.email})
    return schemas.TokenResponse(
        access_token=token, full_name=student.full_name, email=student.email, role=student.role, group=student.group
    )


@app.post("/api/auth/register", response_model=schemas.TokenResponse)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email.endswith(ALLOWED_EMAIL_DOMAIN):
        raise HTTPException(
            status_code=400, detail=f"Debes registrarte con un correo institucional {ALLOWED_EMAIL_DOMAIN}"
        )

    documento = payload.documento.strip()
    if not documento:
        raise HTTPException(status_code=400, detail="El documento de identidad es obligatorio")

    existing = db.query(models.Student).filter(models.Student.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta registrada con ese correo")

    student = models.Student(
        email=email,
        documento=documento,
        hashed_password=hash_password(documento),
        full_name=payload.full_name.strip() if payload.full_name else None,
        role="student",
        group=payload.group,
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    token = create_access_token({"sub": student.email})
    return schemas.TokenResponse(
        access_token=token, full_name=student.full_name, email=student.email, role=student.role, group=student.group
    )


@app.post("/api/auth/change-password")
def change_password(
    payload: schemas.ChangePasswordIn,
    db: Session = Depends(get_db),
    current: models.Student = Depends(get_current_student),
):
    if not verify_password(payload.current_password, current.hashed_password):
        raise HTTPException(status_code=401, detail="La contraseña actual no es correcta")
    current.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"changed": True}


def peek_attempt(db: Session, student: models.Student, exam: models.Exam):
    """Como get_or_create_attempt pero sin crear uno nuevo (para listados de solo lectura)."""
    return (
        db.query(models.ExamAttempt)
        .filter(models.ExamAttempt.student_id == student.id, models.ExamAttempt.exam_id == exam.id)
        .first()
    )


def student_attempt_status_label(db: Session, student: models.Student, exam: models.Exam) -> str:
    attempt = peek_attempt(db, student, exam)
    if attempt is None:
        return "not_started"
    return "finished" if attempt_status(attempt, db)["finished"] else "in_progress"


def student_problem_result(db: Session, student: models.Student, problem: models.Problem):
    """Puntaje/estado de UN estudiante en UN problema, a partir de su entrega (si existe)."""
    submission = (
        db.query(models.Submission)
        .filter(models.Submission.student_id == student.id, models.Submission.problem_id == problem.id)
        .first()
    )
    score = submission.total_score if submission else 0.0
    checks_report = json.loads(submission.checks_report) if submission else []
    return submission, score, checks_report


@app.get("/api/exams", response_model=list[schemas.ExamListOut])
def list_exams(db: Session = Depends(get_db), student: models.Student = Depends(get_current_student)):
    exams = db.query(models.Exam).filter(models.Exam.group == student.group).all()
    results = []
    for exam in exams:
        attempt = peek_attempt(db, student, exam)
        if attempt is None:
            status = "not_started"
        else:
            status = "finished" if attempt_status(attempt, db)["finished"] else "in_progress"
        results.append(
            schemas.ExamListOut(
                id=exam.id,
                title=exam.title,
                description=exam.description,
                duration_minutes=exam.duration_minutes,
                status=status,
                is_open=exam.is_open,
            )
        )
    return results


def resolve_exam_problems(db: Session, student: models.Student, exam: models.Exam) -> list[models.Problem]:
    """Lista ordenada de problemas concretos que le corresponden a ESTE
    estudiante en ESTE examen. Los exámenes legados (sin ExamSlot) siguen
    devolviendo la lista fija de siempre (exam.problems, vía ExamProblem).

    Los exámenes con slots resuelven (y congelan, la primera vez) una
    asignación por estudiante: los slots 'fixed' siempre dan el mismo
    problema; los 'random' sortean `count` problemas del banco indicado,
    distintos para cada estudiante."""
    if not exam.slots:
        return exam.problems

    attempt = get_or_create_attempt(db, student, exam)
    assigned = (
        db.query(models.AttemptProblem)
        .filter(models.AttemptProblem.attempt_id == attempt.id)
        .order_by(models.AttemptProblem.order)
        .all()
    )
    if assigned:
        return [a.problem for a in assigned]

    order = 0
    rows = []
    for slot in sorted(exam.slots, key=lambda s: s.order):
        if slot.kind == "fixed":
            chosen = [slot.problem]
        else:
            pool = [p for p in slot.bank.problems if p.status == "published"]
            chosen = random.sample(pool, min(slot.count, len(pool)))
        for problem in chosen:
            rows.append(
                models.AttemptProblem(attempt_id=attempt.id, slot_id=slot.id, problem_id=problem.id, order=order)
            )
            order += 1

    db.add_all(rows)
    db.commit()
    return [r.problem for r in rows]


def build_exam_out(exam: models.Exam, problems: list[models.Problem]) -> schemas.ExamOut:
    problems_out = [
        schemas.ProblemOut(
            id=problem.id,
            order=i,
            title=problem.title,
            statement_md=problem.statement_md,
            starter_code=problem.starter_code,
            max_score=problem.max_score,
        )
        for i, problem in enumerate(problems)
    ]
    return schemas.ExamOut(
        id=exam.id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        problems=problems_out,
    )


@app.get("/api/exams/{exam_id}", response_model=schemas.ExamOut)
def get_exam(exam_id: int, db: Session = Depends(get_db), student: models.Student = Depends(get_current_student)):
    exam = get_exam_or_404(db, exam_id, group=student.group)
    return build_exam_out(exam, resolve_exam_problems(db, student, exam))


@app.post("/api/exams/{exam_id}/start", response_model=schemas.AttemptOut)
def start_exam(exam_id: int, db: Session = Depends(get_db), student: models.Student = Depends(get_current_student)):
    exam = get_exam_or_404(db, exam_id, group=student.group)
    if not exam.is_open and peek_attempt(db, student, exam) is None:
        raise HTTPException(status_code=403, detail="El docente aún no ha habilitado este examen.")
    attempt = get_or_create_attempt(db, student, exam)
    return attempt_status(attempt, db)


@app.post("/api/exams/{exam_id}/finish", response_model=schemas.AttemptOut)
def finish_exam(exam_id: int, db: Session = Depends(get_db), student: models.Student = Depends(get_current_student)):
    exam = get_exam_or_404(db, exam_id, group=student.group)
    attempt = get_or_create_attempt(db, student, exam)
    if attempt.finished_at is None:
        attempt.finished_at = now()
        db.commit()
        _regrade_attempt(db, student, exam)
    return attempt_status(attempt, db)


@app.get("/api/exams/{exam_id}/results", response_model=schemas.ExamResultsOut)
def exam_results(exam_id: int, db: Session = Depends(get_db), student: models.Student = Depends(get_current_student)):
    exam = get_exam_or_404(db, exam_id, group=student.group)
    attempt = get_or_create_attempt(db, student, exam)
    status = attempt_status(attempt, db)
    if not status["finished"]:
        raise HTTPException(status_code=403, detail="Aún no has finalizado el examen.")

    problems_out = []
    total_score = 0.0
    max_score = 0.0
    for problem in resolve_exam_problems(db, student, exam):
        submission, score, checks_report = student_problem_result(db, student, problem)

        problems_out.append(
            schemas.ProblemResultOut(
                problem_id=problem.id,
                title=problem.title,
                max_score=problem.max_score,
                score=score,
                checks=checks_report,
                code=submission.code if submission else None,
                stdout=submission.stdout if submission else None,
                stderr=submission.stderr if submission else None,
            )
        )
        total_score += score
        max_score += problem.max_score

    return schemas.ExamResultsOut(
        exam_title=exam.title, total_score=total_score, max_score=max_score, problems=problems_out
    )


def _persist_submission(db: Session, student: models.Student, problem: models.Problem, code: str, result: dict, grading: dict) -> models.Submission:
    submission = (
        db.query(models.Submission)
        .filter(models.Submission.student_id == student.id, models.Submission.problem_id == problem.id)
        .first()
    )
    if not submission:
        submission = models.Submission(student_id=student.id, problem_id=problem.id, code=code)
        db.add(submission)

    submission.code = code
    submission.stdout = result["stdout"]
    submission.stderr = result["stderr"]
    submission.total_score = grading["total_score"]
    submission.checks_report = json.dumps(grading["checks_report"])
    db.commit()
    db.refresh(submission)
    return submission


def _regrade_attempt(db: Session, student: models.Student, exam: models.Exam) -> None:
    """Vuelve a ejecutar y calificar el último código GUARDADO (submission.code)
    de cada problema del examen, una sola vez, justo al cerrarse el intento
    (por tiempo o porque el estudiante da "Finalizar"). Necesario porque
    /save-draft (el autoguardado mientras se escribe, ver ProblemCard.jsx)
    persiste el texto pero NUNCA ejecuta ni recalifica: si el estudiante
    edita código y nunca vuelve a pulsar "Ejecutar" ni "Guardar respuesta"
    antes de que se acabe el tiempo, el texto queda guardado pero el
    total_score/checks_report se quedan de la ejecución anterior (o vacíos si
    nunca ejecutó nada) — sin este cierre, el puntaje final no reflejaría lo
    último que el estudiante realmente escribió."""
    for problem in resolve_exam_problems(db, student, exam):
        submission = (
            db.query(models.Submission)
            .filter(models.Submission.student_id == student.id, models.Submission.problem_id == problem.id)
            .first()
        )
        if submission is None:
            continue
        result = run_problem_code(submission.code, problem)
        grading = executor.grade_submission(result, problem)
        _persist_submission(db, student, problem, submission.code, result, grading)


@app.post("/api/problems/{problem_id}/run", response_model=schemas.RunResult)
def run_code(
    problem_id: int,
    payload: schemas.RunRequest,
    db: Session = Depends(get_db),
    student: models.Student = Depends(get_current_student),
):
    problem = get_problem_or_404(db, problem_id)
    exam = get_exam_for_student_problem(db, student, problem)
    require_active_attempt(db, student, exam)

    result = run_problem_code(payload.code, problem)
    grading = executor.grade_submission(result, problem)
    # Ejecutar también guarda: antes solo el botón manual "Guardar respuesta"
    # (POST /save) persistía en la base de datos, así que si el estudiante
    # nunca lo pulsaba explícitamente (o perdía la conexión, o se acababa el
    # tiempo) el código escrito se perdía aunque sí lo hubiera corrido. Ahora
    # cada corrida deja guardado el código y la calificación real, igual que
    # /save (que se conserva para poder guardar sin tener que re-ejecutar).
    _persist_submission(db, student, problem, payload.code, result, grading)

    # En exámenes con tiempo límite (a diferencia de la práctica libre del
    # Simulacro, duration_minutes=None) el estudiante no debe poder saber si
    # su respuesta es correcta -ni ver la solución de referencia- hasta que
    # el examen termine; solo se le muestra stdout/stderr para depurar
    # errores de ejecución. La calificación real ya quedó guardada arriba;
    # el resultado completo se ve en /results una vez finalizado el intento.
    if exam.duration_minutes is not None:
        return schemas.RunResult(
            stdout=result["stdout"],
            stderr=result["stderr"],
            checks=[],
            total_score=0.0,
            max_score=problem.max_score,
            solution_code=None,
        )

    return schemas.RunResult(
        stdout=result["stdout"],
        stderr=result["stderr"],
        checks=grading["checks_report"],
        total_score=grading["total_score"],
        max_score=problem.max_score,
        solution_code=problem.solution_code,
    )


@app.post("/api/problems/{problem_id}/save", response_model=schemas.SaveResult)
def save_code(
    problem_id: int,
    payload: schemas.RunRequest,
    db: Session = Depends(get_db),
    student: models.Student = Depends(get_current_student),
):
    problem = get_problem_or_404(db, problem_id)
    exam = get_exam_for_student_problem(db, student, problem)
    require_active_attempt(db, student, exam)

    result = run_problem_code(payload.code, problem)
    grading = executor.grade_submission(result, problem)
    submission = _persist_submission(db, student, problem, payload.code, result, grading)

    return schemas.SaveResult(saved=True, saved_at=submission.updated_at)


@app.post("/api/problems/{problem_id}/save-draft", response_model=schemas.SaveResult)
def save_draft(
    problem_id: int,
    payload: schemas.RunRequest,
    db: Session = Depends(get_db),
    student: models.Student = Depends(get_current_student),
):
    """Autoguardado liviano: persiste SOLO el texto del código, sin ejecutarlo
    ni recalificar (a diferencia de /run y /save). Pensado para llamarse
    seguido (debounced) mientras el estudiante escribe, para que nunca se
    pierda lo tecleado aunque nunca llegue a pulsar "Ejecutar" o "Guardar
    respuesta" — p.ej. si se acaba el tiempo del examen o se cae la conexión
    justo después de escribir. stdout/stderr/calificación quedan como estén
    (los actualiza la próxima ejecución real vía /run o /save)."""
    problem = get_problem_or_404(db, problem_id)
    exam = get_exam_for_student_problem(db, student, problem)
    require_active_attempt(db, student, exam)

    submission = (
        db.query(models.Submission)
        .filter(models.Submission.student_id == student.id, models.Submission.problem_id == problem.id)
        .first()
    )
    if not submission:
        submission = models.Submission(student_id=student.id, problem_id=problem.id, code=payload.code)
        db.add(submission)
    else:
        submission.code = payload.code
    db.commit()
    db.refresh(submission)

    return schemas.SaveResult(saved=True, saved_at=submission.updated_at)


@app.get("/api/problems/{problem_id}/my-submission", response_model=schemas.MySubmissionOut | None)
def my_submission(
    problem_id: int,
    db: Session = Depends(get_db),
    student: models.Student = Depends(get_current_student),
):
    submission = (
        db.query(models.Submission)
        .filter(models.Submission.student_id == student.id, models.Submission.problem_id == problem_id)
        .first()
    )
    if not submission:
        return None
    return schemas.MySubmissionOut(
        problem_id=submission.problem_id,
        code=submission.code,
        stdout=submission.stdout,
        stderr=submission.stderr,
        saved_at=submission.updated_at,
    )


# ---- Vistas de docente ----


@app.get("/api/teacher/exams/{exam_id}/preview", response_model=schemas.ExamOut)
def teacher_preview_exam(
    exam_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    """Vista previa del examen para el docente: mismos problemas que ve el
    estudiante, pero sin crear un ExamAttempt (sin cronómetro ni límite de
    intentos) — para resolverlo y validar las respuestas antes de publicarlo."""
    exam = get_exam_or_404(db, exam_id, group=teacher.group)
    return build_exam_out(exam, resolve_exam_problems(db, teacher, exam))


@app.post("/api/teacher/problems/{problem_id}/run", response_model=schemas.RunResult)
def teacher_run_code(
    problem_id: int,
    payload: schemas.RunRequest,
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    problem = get_teacher_problem_or_404(db, problem_id, teacher.group)
    result = run_problem_code(payload.code, problem)
    grading = executor.grade_submission(result, problem)
    return schemas.RunResult(
        stdout=result["stdout"],
        stderr=result["stderr"],
        checks=grading["checks_report"],
        total_score=grading["total_score"],
        max_score=problem.max_score,
        solution_code=problem.solution_code,
    )


@app.post("/api/teacher/problems/{problem_id}/save", response_model=schemas.SaveResult)
def teacher_save_code(
    problem_id: int,
    payload: schemas.RunRequest,
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    """Guarda el intento de solución del docente en su propia cuenta (no
    cuenta como Submission de un estudiante: el dashboard filtra por
    role == 'student'), para que pueda retomar la previsualización después."""
    problem = get_teacher_problem_or_404(db, problem_id, teacher.group)
    result = run_problem_code(payload.code, problem)
    grading = executor.grade_submission(result, problem)

    submission = (
        db.query(models.Submission)
        .filter(models.Submission.student_id == teacher.id, models.Submission.problem_id == problem.id)
        .first()
    )
    if not submission:
        submission = models.Submission(student_id=teacher.id, problem_id=problem.id, code=payload.code)
        db.add(submission)

    submission.code = payload.code
    submission.stdout = result["stdout"]
    submission.stderr = result["stderr"]
    submission.total_score = grading["total_score"]
    submission.checks_report = json.dumps(grading["checks_report"])
    db.commit()
    db.refresh(submission)

    return schemas.SaveResult(saved=True, saved_at=submission.updated_at)


def _slugify_filename(text: str) -> str:
    keep = "".join(c for c in text if c.isalnum() or c in " _-").strip()
    return keep.replace(" ", "_") or "examen"


def _slot_representative_problem(slot: models.ExamSlot) -> models.Problem | None:
    """Problema 'representativo' de un slot, para poder mostrar título y
    max_score en el dashboard/export antes (o sin) que ningún estudiante lo
    haya resuelto. Fijo -> el problema mismo; aleatorio -> el primero del
    banco (asume, como pasa hoy en los bancos existentes, que todos los
    problemas de un mismo banco reparten el mismo total de puntos)."""
    if slot.kind == "fixed":
        return slot.problem
    return slot.bank.problems[0] if slot.bank.problems else None


def compute_exam_dashboard(db: Session, exam: models.Exam) -> schemas.TeacherExamDashboardOut:
    students = (
        db.query(models.Student)
        .filter(models.Student.role == "student", models.Student.group == exam.group)
        .order_by(models.Student.full_name)
        .all()
    )

    is_random = bool(exam.slots)
    num_slots = len(exam.slots) if is_random else len(exam.problems)
    slot_titles = []
    slot_max_scores = []
    if is_random:
        for i, slot in enumerate(sorted(exam.slots, key=lambda s: s.order)):
            rep = _slot_representative_problem(slot)
            slot_max_scores.append(rep.max_score if rep else 0.0)
            slot_titles.append(rep.title if slot.kind == "fixed" and rep else f"Ejercicio {i + 1} — banco {slot.bank.title}")
    max_score = sum(slot_max_scores) if is_random else sum(p.max_score for p in exam.problems)

    status_counts = {"not_started": 0, "in_progress": 0, "finished": 0}
    finished_totals = []
    student_rows = []
    problem_scores = {i: [] for i in range(num_slots)} if is_random else {p.id: [] for p in exam.problems}
    criteria_pass = {} if is_random else {p.id: {} for p in exam.problems}

    for student in students:
        status = student_attempt_status_label(db, student, exam)
        status_counts[status] += 1

        row_scores = []
        total = 0.0
        if is_random:
            # No crear un intento como efecto secundario de que el docente
            # mire el dashboard: si el estudiante no ha empezado, no hay
            # nada sorteado todavía para él/ella.
            has_attempt = peek_attempt(db, student, exam) is not None
            problems = resolve_exam_problems(db, student, exam) if has_attempt else [None] * num_slots
        else:
            problems = exam.problems

        for idx, problem in enumerate(problems):
            if problem is None:
                row_scores.append(0.0)
                continue
            key = idx if is_random else problem.id
            _submission, score, checks_report = student_problem_result(db, student, problem)
            row_scores.append(score)
            total += score
            if status == "finished":
                problem_scores[key].append(score)
                if not is_random:
                    bucket = criteria_pass[key]
                    for check in checks_report:
                        bucket[check["label"]] = bucket.get(check["label"], 0) + (1 if check["passed"] else 0)

        nota_5 = round((total / max_score) * 5, 2) if max_score > 0 else 0.0
        student_rows.append(
            schemas.StudentRowOut(
                student_id=student.id,
                full_name=student.full_name,
                email=student.email,
                documento=student.documento,
                status=status,
                total_score=total,
                max_score=max_score,
                nota_5=nota_5,
                problem_scores=row_scores,
            )
        )
        if status == "finished":
            finished_totals.append(total)

    avg_score = sum(finished_totals) / len(finished_totals) if finished_totals else 0.0
    avg_nota_5 = round((avg_score / max_score) * 5, 2) if max_score > 0 else 0.0

    bucket_ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100.001)]
    distribution = []
    for lo, hi in bucket_ranges:
        count = 0
        for total in finished_totals:
            pct = (total / max_score * 100) if max_score > 0 else 0.0
            if lo <= pct < hi:
                count += 1
        distribution.append(schemas.ScoreBucketOut(label=f"{lo:.0f}-{min(hi, 100):.0f}%", count=count))

    finished_n = status_counts["finished"]
    problems_out = []
    if is_random:
        for idx, slot in enumerate(sorted(exam.slots, key=lambda s: s.order)):
            scores = problem_scores[idx]
            avg_p = sum(scores) / len(scores) if scores else 0.0
            # Desglose por criterio omitido a propósito para slots aleatorios:
            # cada estudiante puede haber recibido un problema distinto del
            # mismo banco, con etiquetas de check distintas (ej. distintos
            # argumentos en el enunciado) — mezclarlas en un solo pass-rate
            # sería un dato confuso. Para slots fijos sí se calcula, igual
            # que siempre (rama de abajo).
            problems_out.append(
                schemas.ProblemStatOut(
                    problem_id=slot.problem_id or 0,
                    title=slot_titles[idx],
                    max_score=slot_max_scores[idx],
                    avg_score=avg_p,
                    criteria=[],
                )
            )
    else:
        for problem in exam.problems:
            scores = problem_scores[problem.id]
            avg_p = sum(scores) / len(scores) if scores else 0.0
            criteria_out = []
            for check_cfg in json.loads(problem.rubric or "[]"):
                passed_count = criteria_pass[problem.id].get(check_cfg["label"], 0)
                rate = (passed_count / finished_n * 100) if finished_n else 0.0
                criteria_out.append(
                    schemas.CriterionStatOut(label=check_cfg["label"], max_points=check_cfg["points"], pass_rate=rate)
                )
            problems_out.append(
                schemas.ProblemStatOut(
                    problem_id=problem.id,
                    title=problem.title,
                    max_score=problem.max_score,
                    avg_score=avg_p,
                    criteria=criteria_out,
                )
            )

    return schemas.TeacherExamDashboardOut(
        exam_id=exam.id,
        exam_title=exam.title,
        total_students=len(students),
        not_started=status_counts["not_started"],
        in_progress=status_counts["in_progress"],
        finished=status_counts["finished"],
        avg_score=avg_score,
        avg_nota_5=avg_nota_5,
        max_score=max_score,
        score_distribution=distribution,
        problems=problems_out,
        students=student_rows,
    )


def _to_teacher_list_out(db: Session, exam: models.Exam) -> schemas.TeacherExamListOut:
    dashboard = compute_exam_dashboard(db, exam)
    return schemas.TeacherExamListOut(
        id=exam.id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        is_open=exam.is_open,
        total_students=dashboard.total_students,
        not_started=dashboard.not_started,
        in_progress=dashboard.in_progress,
        finished=dashboard.finished,
        avg_score=dashboard.avg_score,
        max_score=dashboard.max_score,
    )


@app.get("/api/teacher/exams", response_model=list[schemas.TeacherExamListOut])
def teacher_list_exams(db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)):
    exams = db.query(models.Exam).filter(models.Exam.group == teacher.group).all()
    return [_to_teacher_list_out(db, exam) for exam in exams]


@app.get("/api/teacher/banks", response_model=list[schemas.BankOut])
def teacher_list_banks(
    published_only: bool = False,
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    """Por defecto devuelve todos los problemas de cada banco (incl.
    borradores, para la pantalla de gestión de bancos). Con
    ?published_only=true (usado al armar un examen) solo devuelve los
    publicados, para que un borrador sin revisar no pueda terminar en un
    examen real."""
    banks = db.query(models.ProblemBank).filter(models.ProblemBank.group == teacher.group).all()
    return [
        schemas.BankOut(
            id=bank.id,
            title=bank.title,
            description=bank.description,
            problems=[
                schemas.BankProblemOut(
                    id=p.id, title=p.title, max_score=p.max_score, status=p.status, review_notes=p.review_notes
                )
                for p in bank.problems
                if not published_only or p.status == "published"
            ],
        )
        for bank in banks
    ]


@app.get("/api/teacher/problems/{problem_id}", response_model=schemas.TeacherProblemDetailOut)
def teacher_get_problem_detail(
    problem_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    problem = get_teacher_problem_or_404(db, problem_id, teacher.group)
    return schemas.TeacherProblemDetailOut(
        id=problem.id,
        bank_id=problem.bank_id,
        bank_title=problem.bank.title,
        title=problem.title,
        statement_md=problem.statement_md,
        starter_code=problem.starter_code,
        solution_code=problem.solution_code,
        rubric=json.loads(problem.rubric or "[]"),
        max_score=problem.max_score,
        status=problem.status,
        review_notes=problem.review_notes,
    )


@app.post("/api/teacher/problems/{problem_id}/publish", response_model=schemas.BankProblemOut)
def teacher_publish_problem(
    problem_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    """Marca un problema borrador (generado por el pipeline de agentes IA o
    creado a mano) como publicado, habilitándolo para usarse en exámenes."""
    problem = get_teacher_problem_or_404(db, problem_id, teacher.group)
    problem.status = "published"
    db.commit()
    return schemas.BankProblemOut(
        id=problem.id,
        title=problem.title,
        max_score=problem.max_score,
        status=problem.status,
        review_notes=problem.review_notes,
    )


@app.delete("/api/teacher/problems/{problem_id}")
def teacher_delete_problem(
    problem_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    """Borra un problema del banco. Se rechaza si el problema está en uso
    (parte de un examen, ya sorteado a algún estudiante, o con entregas
    guardadas), para no romper exámenes existentes ni perder datos de
    estudiantes. Para quitar un problema que sí está en uso, primero hay que
    eliminar el examen que lo usa (ver DELETE /api/teacher/exams/{id})."""
    problem = get_teacher_problem_or_404(db, problem_id, teacher.group)
    blockers = get_problem_usage_blockers(db, problem_id)
    if blockers:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar '{problem.title}': " + "; ".join(blockers) + ".",
        )
    db.delete(problem)
    db.commit()
    return {"deleted": True, "problem_id": problem_id}


@app.delete("/api/teacher/banks/{bank_id}")
def teacher_delete_bank(
    bank_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    """Borra un banco completo (y sus problemas). Se rechaza si el banco se
    usa como fuente de sorteo en algún examen, o si alguno de sus problemas
    está en uso (ver teacher_delete_problem) — hay que resolver eso primero
    (normalmente eliminando el examen que lo usa)."""
    bank = get_bank_or_404(db, bank_id, group=teacher.group)

    blockers = []
    slots_using_bank = db.query(models.ExamSlot).filter(models.ExamSlot.bank_id == bank_id).all()
    for slot in slots_using_bank:
        blockers.append(f"el banco se usa como sorteo aleatorio en el examen '{slot.exam.title}'")

    for problem in bank.problems:
        problem_blockers = get_problem_usage_blockers(db, problem.id)
        if problem_blockers:
            blockers.append(f"el problema '{problem.title}' " + "; ".join(problem_blockers))

    if blockers:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el banco '{bank.title}': " + "; ".join(blockers) + ".",
        )

    for problem in list(bank.problems):
        db.delete(problem)
    db.delete(bank)
    db.commit()
    return {"deleted": True, "bank_id": bank_id}


@app.post("/api/teacher/banks", response_model=schemas.BankOut)
def teacher_create_bank(
    payload: schemas.TeacherCreateBankIn,
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="El banco necesita un título.")

    bank = models.ProblemBank(title=title, description=payload.description, group=teacher.group)
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return schemas.BankOut(id=bank.id, title=bank.title, description=bank.description, problems=[])


@app.post("/api/teacher/banks/{bank_id}/load-from-tex", response_model=schemas.LoadTexResultOut)
def teacher_load_bank_from_tex(
    bank_id: int,
    file: UploadFile = File(...),
    max_problems: int | None = Form(None),
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    """Sube un .tex y corre el pipeline de 4 agentes IA (Gemini) para
    generar problemas dentro de este banco. Igual que el CLI
    load_problems_from_tex.py: todo entra como status="draft" (ver
    gemini_agents.orchestrate_load_tex) — nunca se usa en un examen hasta
    que el docente lo publique. Llamada síncrona: puede tardar varios
    minutos si hay varios problemas en el .tex."""
    get_bank_or_404(db, bank_id, group=teacher.group)

    if not file.filename.lower().endswith(".tex"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .tex")

    content = file.file.read()
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".tex", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = orchestrate_load_tex(tmp_path, bank_id, db, max_problems=max_problems)
    except QuotaExceededError as e:
        raise HTTPException(status_code=429, detail=f"Cupo diario propio de Gemini agotado: {e}.")
    finally:
        os.unlink(tmp_path)

    usage = get_usage_today()
    return schemas.LoadTexResultOut(
        bank_id=result["bank_id"],
        created=result["created"],
        skipped=result["skipped"],
        calls_today=usage["calls"],
        tokens_today=usage["tokens"],
    )


@app.post("/api/teacher/exams", response_model=schemas.TeacherExamListOut)
def teacher_create_exam(
    payload: schemas.TeacherCreateExamIn,
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="El examen necesita un título.")
    if not payload.slots:
        raise HTTPException(status_code=400, detail="El examen necesita al menos un ejercicio.")

    exam = models.Exam(
        title=title,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        is_open=False,
        group=teacher.group,
    )
    db.add(exam)
    db.flush()

    for order, slot_in in enumerate(payload.slots):
        if slot_in.kind == "fixed":
            problem = get_teacher_problem_or_404(db, slot_in.problem_id, teacher.group)
            if problem.status != "published":
                raise HTTPException(
                    status_code=400,
                    detail=f"El problema '{problem.title}' es un borrador sin revisar; publícalo antes de usarlo en un examen.",
                )
            db.add(models.ExamSlot(exam_id=exam.id, order=order, kind="fixed", problem_id=problem.id))
        elif slot_in.kind == "random":
            bank = get_bank_or_404(db, slot_in.bank_id, group=teacher.group)
            published = [p for p in bank.problems if p.status == "published"]
            count = max(1, slot_in.count or 1)
            if count > len(published):
                raise HTTPException(
                    status_code=400,
                    detail=f"El banco '{bank.title}' solo tiene {len(published)} problema(s) publicado(s), no se pueden pedir {count}.",
                )
            db.add(models.ExamSlot(exam_id=exam.id, order=order, kind="random", bank_id=bank.id, count=count))
        else:
            raise HTTPException(status_code=400, detail=f"Tipo de ejercicio inválido: {slot_in.kind!r}")

    db.commit()
    db.refresh(exam)
    return _to_teacher_list_out(db, exam)


@app.post("/api/teacher/exams/{exam_id}/toggle-open", response_model=schemas.TeacherToggleOpenOut)
def teacher_toggle_exam_open(
    exam_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    """Habilita/deshabilita el acceso de los estudiantes al examen. Cerrarlo
    no afecta a quienes ya tienen un intento en curso — solo bloquea intentos
    nuevos (ver start_exam)."""
    exam = get_exam_or_404(db, exam_id, group=teacher.group)
    exam.is_open = not exam.is_open
    db.commit()
    return schemas.TeacherToggleOpenOut(exam_id=exam.id, is_open=exam.is_open)


@app.delete("/api/teacher/exams/{exam_id}")
def teacher_delete_exam(
    exam_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    """Elimina el examen y TODOS los datos de estudiantes asociados a sus
    problemas: intentos (ExamAttempt/AttemptProblem) y entregas (Submission),
    incluso si algún problema también aparece en otro examen (banco
    compartido) — en ese caso el trabajo guardado en ese otro examen también
    se pierde. Esta es una acción destructiva e irreversible."""
    exam = get_exam_or_404(db, exam_id, group=teacher.group)

    problem_ids = {ep.problem_id for ep in exam.exam_problems}
    for slot in exam.slots:
        if slot.kind == "fixed" and slot.problem_id is not None:
            problem_ids.add(slot.problem_id)
        elif slot.kind == "random" and slot.bank_id is not None:
            problem_ids.update(p.id for p in slot.bank.problems)

    if problem_ids:
        db.query(models.Submission).filter(models.Submission.problem_id.in_(problem_ids)).delete(
            synchronize_session=False
        )

    attempt_ids = [
        row.id for row in db.query(models.ExamAttempt.id).filter(models.ExamAttempt.exam_id == exam_id).all()
    ]
    if attempt_ids:
        db.query(models.AttemptProblem).filter(models.AttemptProblem.attempt_id.in_(attempt_ids)).delete(
            synchronize_session=False
        )
    db.query(models.ExamAttempt).filter(models.ExamAttempt.exam_id == exam_id).delete(synchronize_session=False)

    db.delete(exam)
    db.commit()
    return {"deleted": True, "exam_id": exam_id}


@app.get(
    "/api/teacher/exams/{exam_id}/students/{student_id}/submissions",
    response_model=schemas.ExamResultsOut,
)
def teacher_student_submissions(
    exam_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    exam = get_exam_or_404(db, exam_id, group=teacher.group)
    student = (
        db.query(models.Student)
        .filter(
            models.Student.id == student_id,
            models.Student.role == "student",
            models.Student.group == teacher.group,
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    problems_out = []
    total_score = 0.0
    max_score = 0.0
    for problem in resolve_exam_problems(db, student, exam):
        submission, score, checks_report = student_problem_result(db, student, problem)
        problems_out.append(
            schemas.ProblemResultOut(
                problem_id=problem.id,
                title=problem.title,
                max_score=problem.max_score,
                score=score,
                checks=checks_report,
                code=submission.code if submission else None,
                stdout=submission.stdout if submission else None,
                stderr=submission.stderr if submission else None,
            )
        )
        total_score += score
        max_score += problem.max_score

    return schemas.ExamResultsOut(
        exam_title=f"{exam.title} — {student.full_name or student.email}",
        total_score=total_score,
        max_score=max_score,
        problems=problems_out,
    )


@app.get("/api/teacher/exams/{exam_id}/dashboard", response_model=schemas.TeacherExamDashboardOut)
def teacher_exam_dashboard(
    exam_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    exam = get_exam_or_404(db, exam_id, group=teacher.group)
    return compute_exam_dashboard(db, exam)


@app.get("/api/teacher/exams/{exam_id}/export.xlsx")
def teacher_export_xlsx(
    exam_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    exam = get_exam_or_404(db, exam_id, group=teacher.group)
    dashboard = compute_exam_dashboard(db, exam)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"

    headers = ["Documento", "Apellidos y nombre", "Correo", "Estado"]
    for problem in dashboard.problems:
        headers.append(f"{problem.title} ({problem.max_score:.0f} pts)")
    headers += ["Total", "Máximo", "Nota (0-5)"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    status_labels = {"not_started": "No iniciado", "in_progress": "En progreso", "finished": "Finalizado"}
    for row in dashboard.students:
        ws.append(
            [
                row.documento,
                row.full_name or "",
                row.email,
                status_labels.get(row.status, row.status),
                *row.problem_scores,
                row.total_score,
                row.max_score,
                row.nota_5,
            ]
        )

    for col in ws.columns:
        length = max((len(str(c.value)) if c.value is not None else 0) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(length + 2, 10), 45)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"resultados_{_slugify_filename(exam.title)}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---- Vistas de admin (gestión de cuentas docente, una por grupo) ----

DEFAULT_TEACHER_PASSWORD = "123456789"


@app.get("/api/admin/teachers", response_model=list[schemas.AdminTeacherOut])
def admin_list_teachers(db: Session = Depends(get_db), admin: models.Student = Depends(get_current_admin)):
    return (
        db.query(models.Student)
        .filter(models.Student.role == "teacher")
        .order_by(models.Student.group)
        .all()
    )


@app.post("/api/admin/teachers", response_model=schemas.AdminTeacherOut)
def admin_create_teacher(
    payload: schemas.AdminTeacherIn,
    db: Session = Depends(get_db),
    admin: models.Student = Depends(get_current_admin),
):
    """Crea una cuenta docente para un grupo. La contraseña inicial siempre es
    DEFAULT_TEACHER_PASSWORD — el docente la cambia con POST
    /api/auth/change-password la primera vez que entra. No exige correo
    institucional: estas cuentas no pasan por el auto-registro público."""
    email = payload.email.strip().lower()
    existing = db.query(models.Student).filter(models.Student.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta registrada con ese correo")

    teacher = models.Student(
        email=email,
        documento="-",
        hashed_password=hash_password(DEFAULT_TEACHER_PASSWORD),
        full_name=payload.full_name.strip(),
        role="teacher",
        group=payload.group,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@app.delete("/api/admin/teachers/{teacher_id}")
def admin_delete_teacher(
    teacher_id: int, db: Session = Depends(get_db), admin: models.Student = Depends(get_current_admin)
):
    teacher = (
        db.query(models.Student)
        .filter(models.Student.id == teacher_id, models.Student.role == "teacher")
        .first()
    )
    if not teacher:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    db.delete(teacher)
    db.commit()
    return {"deleted": True, "teacher_id": teacher_id}


# ---- Roster de estudiantes del grupo (docente) ----


@app.get("/api/teacher/students", response_model=list[schemas.StudentRosterOut])
def teacher_list_students(db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)):
    return (
        db.query(models.Student)
        .filter(models.Student.role == "student", models.Student.group == teacher.group)
        .order_by(models.Student.full_name)
        .all()
    )


@app.post("/api/teacher/students", response_model=schemas.StudentRosterOut)
def teacher_add_student(
    payload: schemas.AddStudentIn,
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    email = payload.email.strip().lower()
    documento = payload.documento.strip()
    if not documento:
        raise HTTPException(status_code=400, detail="El documento de identidad es obligatorio")
    if db.query(models.Student).filter(models.Student.email == email).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta registrada con ese correo")

    student = models.Student(
        email=email,
        documento=documento,
        hashed_password=hash_password(documento),
        full_name=_normalize_name(payload.full_name),
        role="student",
        group=teacher.group,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.delete("/api/teacher/students/{student_id}")
def teacher_delete_student(
    student_id: int, db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)
):
    student = (
        db.query(models.Student)
        .filter(
            models.Student.id == student_id,
            models.Student.role == "student",
            models.Student.group == teacher.group,
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    db.query(models.Submission).filter(models.Submission.student_id == student.id).delete(synchronize_session=False)
    attempt_ids = [
        row.id for row in db.query(models.ExamAttempt.id).filter(models.ExamAttempt.student_id == student.id).all()
    ]
    if attempt_ids:
        db.query(models.AttemptProblem).filter(models.AttemptProblem.attempt_id.in_(attempt_ids)).delete(
            synchronize_session=False
        )
    db.query(models.ExamAttempt).filter(models.ExamAttempt.student_id == student.id).delete(
        synchronize_session=False
    )
    db.delete(student)
    db.commit()
    return {"deleted": True, "student_id": student_id}


@app.delete("/api/teacher/students")
def teacher_delete_group(db: Session = Depends(get_db), teacher: models.Student = Depends(get_current_teacher)):
    """Elimina TODO el roster del grupo del docente (y sus intentos/entregas).
    Acción destructiva e irreversible — pensada para arrancar un semestre
    nuevo desde cero."""
    student_ids = [
        row.id
        for row in db.query(models.Student.id)
        .filter(models.Student.role == "student", models.Student.group == teacher.group)
        .all()
    ]
    if student_ids:
        db.query(models.Submission).filter(models.Submission.student_id.in_(student_ids)).delete(
            synchronize_session=False
        )
        attempt_ids = [
            row.id
            for row in db.query(models.ExamAttempt.id).filter(models.ExamAttempt.student_id.in_(student_ids)).all()
        ]
        if attempt_ids:
            db.query(models.AttemptProblem).filter(models.AttemptProblem.attempt_id.in_(attempt_ids)).delete(
                synchronize_session=False
            )
        db.query(models.ExamAttempt).filter(models.ExamAttempt.student_id.in_(student_ids)).delete(
            synchronize_session=False
        )
        db.query(models.Student).filter(models.Student.id.in_(student_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": True, "count": len(student_ids)}


ROSTER_COLUMNS = {
    "nombres y apellidos": "full_name",
    "documento": "documento",
    "correo": "email",
    "grupo": "group",
}


@app.post("/api/teacher/students/import-xlsx", response_model=schemas.ImportRosterResultOut)
def teacher_import_students_xlsx(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    teacher: models.Student = Depends(get_current_teacher),
):
    """Carga masiva del roster desde un .xlsx con columnas obligatorias
    (por nombre de encabezado, sin importar mayúsculas): Nombres y Apellidos,
    Documento, Correo, Grupo. Filas cuyo Grupo no coincida con el del docente
    que sube el archivo se rechazan (se reportan, no se importan); el resto
    se crea con el mismo convenio de import_students.py (password=documento,
    dedup por email)."""
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .xlsx")

    try:
        wb = load_workbook(io.BytesIO(file.file.read()), data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo .xlsx")
    ws = wb.active

    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not header_row:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    col_index = {}
    for i, cell in enumerate(header_row):
        key = str(cell or "").strip().lower()
        if key in ROSTER_COLUMNS:
            col_index[ROSTER_COLUMNS[key]] = i

    missing = [h for h in ("full_name", "documento", "email", "group") if h not in col_index]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Faltan columnas obligatorias: Nombres y Apellidos, Documento, Correo, Grupo.",
        )

    created, skipped, rejected = 0, 0, []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row is None or all(c is None for c in row):
            continue

        raw_group = row[col_index["group"]]
        try:
            row_group = int(raw_group)
        except (TypeError, ValueError):
            rejected.append(schemas.RosterRejectedRowOut(row=row_idx, motivo="Grupo inválido"))
            continue
        if row_group != teacher.group:
            rejected.append(
                schemas.RosterRejectedRowOut(
                    row=row_idx, motivo=f"Grupo {row_group} no coincide con tu grupo ({teacher.group})"
                )
            )
            continue

        raw_email = row[col_index["email"]]
        email = str(raw_email or "").strip().lower()
        if not email:
            rejected.append(schemas.RosterRejectedRowOut(row=row_idx, motivo="Correo vacío"))
            continue

        raw_documento = row[col_index["documento"]]
        if isinstance(raw_documento, float) and raw_documento.is_integer():
            documento = str(int(raw_documento))
        else:
            documento = str(raw_documento or "").strip()
        if not documento:
            rejected.append(schemas.RosterRejectedRowOut(row=row_idx, motivo="Documento vacío"))
            continue

        if db.query(models.Student).filter(models.Student.email == email).first():
            skipped += 1
            continue

        full_name = _normalize_name(str(row[col_index["full_name"]] or ""))
        db.add(
            models.Student(
                email=email,
                documento=documento,
                hashed_password=hash_password(documento),
                full_name=full_name,
                role="student",
                group=row_group,
            )
        )
        created += 1

    db.commit()
    return schemas.ImportRosterResultOut(created=created, skipped=skipped, rejected=rejected)


# ---- Frontend estático (solo presente en la imagen de Docker) ----
# En desarrollo local, el frontend se sirve aparte con "npm run dev" (Vite) y
# esta carpeta no existe, así que este bloque simplemente no se activa.

FRONTEND_DIST = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend_dist"))

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

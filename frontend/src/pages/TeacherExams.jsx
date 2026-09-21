import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import * as api from "../api";
import ChangePasswordForm from "../components/ChangePasswordForm";

export default function TeacherExams() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api
      .getTeacherExams()
      .then(setExams)
      .catch(() => navigate("/"))
      .finally(() => setLoading(false));
  }, []);

  async function handleToggle(examId) {
    setTogglingId(examId);
    try {
      const { is_open } = await api.toggleExamOpen(examId);
      setExams((prev) => prev.map((e) => (e.id === examId ? { ...e, is_open } : e)));
    } finally {
      setTogglingId(null);
    }
  }

  async function handleDelete(exam) {
    const confirmed = window.confirm(
      `¿Eliminar el examen "${exam.title}"?\n\nEsto borrará también, de forma permanente, todos los intentos y entregas guardadas por los estudiantes en sus problemas (incluso si algún problema se comparte con otro examen). Esta acción no se puede deshacer.`
    );
    if (!confirmed) return;

    setDeletingId(exam.id);
    try {
      await api.deleteTeacherExam(exam.id);
      setExams((prev) => prev.filter((e) => e.id !== exam.id));
    } catch (err) {
      window.alert("No se pudo eliminar el examen. Intenta de nuevo.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-fuchsia-500 flex items-center justify-center text-white font-bold">
              ∑
            </div>
            <span className="text-white font-semibold">Métodos Numéricos · Docente</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm hidden sm:block">
              {user?.full_name || user?.email}
            </span>
            <Link
              to="/teacher/students"
              className="text-sm text-slate-300 hover:text-white border border-white/10 rounded-lg px-3 py-1.5 hover:bg-white/5 transition"
            >
              Estudiantes
            </Link>
            <ChangePasswordForm />
            <button
              onClick={() => {
                signOut();
                navigate("/");
              }}
              className="text-sm text-slate-300 hover:text-white border border-white/10 rounded-lg px-3 py-1.5 hover:bg-white/5 transition"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between gap-4 mb-1">
          <h1 className="text-2xl font-bold text-white">Exámenes</h1>
          <div className="flex items-center gap-3">
            <Link
              to="/teacher/banks"
              className="shrink-0 rounded-lg border border-white/10 hover:bg-white/5 text-slate-200 text-sm font-medium px-4 py-2 transition"
            >
              🗄 Bancos de problemas
            </Link>
            <Link
              to="/teacher/exams/new"
              className="shrink-0 rounded-lg bg-brand-600/80 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 transition"
            >
              + Crear examen
            </Link>
          </div>
        </div>
        <p className="text-slate-400 mb-8">Selecciona un examen para ver el dashboard y descargar resultados.</p>

        {loading && <p className="text-slate-500">Cargando...</p>}

        <div className="grid gap-4 sm:grid-cols-2">
          {exams.map((exam) => (
            <div
              key={exam.id}
              className="group rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-brand-400/40 transition p-5 shadow-lg shadow-black/20"
            >
              <div className="flex items-start justify-between gap-2">
                <h2 className="text-lg font-semibold text-white group-hover:text-brand-300 transition">
                  {exam.title}
                </h2>
                <span
                  className={`shrink-0 text-xs font-medium rounded-full border px-2.5 py-1 ${
                    exam.is_open
                      ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                      : "bg-slate-500/15 text-slate-400 border-slate-500/30"
                  }`}
                >
                  {exam.is_open ? "Habilitado" : "Deshabilitado"}
                </span>
              </div>
              <p className="text-slate-400 text-sm mt-2">{exam.description}</p>
              <p className="text-xs mt-2 text-slate-500">
                {exam.max_violations > 0
                  ? `🔒 Control de ventana: se anula con ${exam.max_violations} salidas`
                  : "Sin control de ventana"}
              </p>

              <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                <div className="rounded-lg bg-black/20 py-2">
                  <p className="text-white font-semibold">{exam.total_students}</p>
                  <p className="text-slate-500 text-xs">estudiantes</p>
                </div>
                <div className="rounded-lg bg-black/20 py-2">
                  <p className="text-emerald-400 font-semibold">{exam.finished}</p>
                  <p className="text-slate-500 text-xs">finalizados</p>
                </div>
                <div className="rounded-lg bg-black/20 py-2">
                  <p className="text-brand-300 font-semibold">{exam.avg_score.toFixed(1)}</p>
                  <p className="text-slate-500 text-xs">prom. / {exam.max_score.toFixed(0)}</p>
                </div>
              </div>

              <div className="flex items-center gap-4 mt-3">
                <Link to={`/teacher/exams/${exam.id}`} className="text-brand-300 hover:text-brand-200 text-sm transition">
                  Ver dashboard →
                </Link>
                <Link
                  to={`/teacher/exams/${exam.id}/preview`}
                  className="text-amber-400 hover:text-amber-300 text-sm transition"
                >
                  👁 Previsualizar →
                </Link>
              </div>

              <button
                onClick={() => handleToggle(exam.id)}
                disabled={togglingId === exam.id}
                className={`w-full mt-4 rounded-lg text-sm font-medium px-4 py-2 transition disabled:opacity-60 ${
                  exam.is_open
                    ? "bg-rose-600/20 text-rose-300 border border-rose-500/30 hover:bg-rose-600/30"
                    : "bg-emerald-600/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-600/30"
                }`}
              >
                {togglingId === exam.id
                  ? "Actualizando..."
                  : exam.is_open
                  ? "Deshabilitar examen"
                  : "Habilitar examen"}
              </button>

              <button
                onClick={() => handleDelete(exam)}
                disabled={deletingId === exam.id}
                className="w-full mt-2 rounded-lg text-sm font-medium px-4 py-2 transition disabled:opacity-60 bg-red-950/40 text-red-400 border border-red-900/50 hover:bg-red-900/40 hover:text-red-300"
              >
                {deletingId === exam.id ? "Eliminando..." : "🗑 Eliminar examen"}
              </button>
            </div>
          ))}
        </div>

        {!loading && exams.length === 0 && (
          <p className="text-slate-500">No hay exámenes disponibles todavía.</p>
        )}
      </main>
    </div>
  );
}

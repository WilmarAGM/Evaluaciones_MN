import { Fragment, useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import * as api from "../api";

const STATUS_LABEL = {
  not_started: "No iniciado",
  in_progress: "En progreso",
  finished: "Finalizado",
};

const STATUS_CLS = {
  not_started: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  in_progress: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  finished: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

function StatCard({ label, value, accent }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center shadow-lg shadow-black/20">
      <p className={`text-2xl font-bold ${accent || "text-white"}`}>{value}</p>
      <p className="text-slate-500 text-xs mt-1">{label}</p>
    </div>
  );
}

export default function TeacherExamDashboard() {
  const { examId } = useParams();
  const [dash, setDash] = useState(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [detailsById, setDetailsById] = useState({});
  const [loadingId, setLoadingId] = useState(null);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  function loadDashboard() {
    return api
      .getTeacherDashboard(examId)
      .then(setDash)
      .catch(() => setError("No se pudo cargar el dashboard."));
  }

  useEffect(() => {
    loadDashboard();
  }, [examId]);

  async function reinstate(studentId) {
    if (!window.confirm("¿Reactivar este intento? Recuperará su nota real (se recalifica lo que alcanzó a guardar).")) return;
    try {
      await api.reinstateAttempt(examId, studentId);
      setDetailsById((prev) => {
        const next = { ...prev };
        delete next[studentId];
        return next;
      });
      setExpandedId(null);
      await loadDashboard();
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo reactivar el intento.");
    }
  }

  async function toggleStudent(studentId) {
    if (expandedId === studentId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(studentId);
    if (!detailsById[studentId]) {
      setLoadingId(studentId);
      try {
        const data = await api.getTeacherStudentSubmissions(examId, studentId);
        setDetailsById((prev) => ({ ...prev, [studentId]: data }));
      } catch {
        setDetailsById((prev) => ({ ...prev, [studentId]: { error: true } }));
      } finally {
        setLoadingId(null);
      }
    }
  }

  async function handleDownload() {
    setDownloading(true);
    try {
      await api.downloadExamXlsx(examId, `resultados_${dash?.exam_title || examId}.xlsx`.replace(/\s+/g, "_"));
    } finally {
      setDownloading(false);
    }
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center text-rose-400">{error}</div>
    );
  }
  if (!dash) {
    return (
      <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center text-slate-400">
        Cargando dashboard...
      </div>
    );
  }

  const maxBucket = Math.max(1, ...dash.score_distribution.map((b) => b.count));

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/teacher/exams" className="text-slate-400 hover:text-white text-sm">
            ← Exámenes
          </Link>
          <div className="flex-1">
            <h1 className="text-white font-semibold">{dash.exam_title}</h1>
          </div>
          <span className="text-slate-400 text-sm hidden sm:block">{user?.full_name || user?.email}</span>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="rounded-lg bg-gradient-to-r from-brand-600 to-fuchsia-600 hover:from-brand-500 hover:to-fuchsia-500 transition text-white text-sm font-medium px-4 py-2 disabled:opacity-60"
          >
            {downloading ? "Generando..." : "⬇ Descargar .xlsx"}
          </button>
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
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 space-y-8 pb-24">
        {/* Resumen general */}
        <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard label="Estudiantes" value={dash.total_students} />
          <StatCard label="No iniciado" value={dash.not_started} accent="text-slate-400" />
          <StatCard label="En progreso" value={dash.in_progress} accent="text-amber-400" />
          <StatCard label="Finalizado" value={dash.finished} accent="text-emerald-400" />
          <StatCard label="Promedio" value={`${dash.avg_score.toFixed(1)} / ${dash.max_score.toFixed(0)}`} accent="text-brand-300" />
          <StatCard label="Nota promedio" value={dash.avg_nota_5.toFixed(2)} accent="text-brand-300" />
        </section>

        {/* Distribución de notas */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-lg shadow-black/20">
          <h2 className="text-white font-semibold mb-4">Distribución de puntajes (finalizados)</h2>
          <div className="flex items-end gap-3 h-32">
            {dash.score_distribution.map((b) => (
              <div key={b.label} className="flex-1 flex flex-col items-center gap-1.5">
                <div
                  className="w-full rounded-t-lg bg-gradient-to-t from-brand-600 to-fuchsia-500"
                  style={{ height: `${(b.count / maxBucket) * 100}%`, minHeight: b.count > 0 ? "6px" : "2px" }}
                />
                <span className="text-white text-xs font-medium">{b.count}</span>
                <span className="text-slate-500 text-xs">{b.label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Por problema */}
        <section className="space-y-4">
          <h2 className="text-white font-semibold">Desempeño por problema</h2>
          {dash.problems.map((p) => (
            <div key={p.problem_id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-lg shadow-black/20">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-medium">{p.title}</h3>
                <span className="text-sm text-slate-300">
                  prom. {p.avg_score.toFixed(1)} / {p.max_score.toFixed(0)}
                </span>
              </div>
              <div className="space-y-2">
                {p.criteria.map((c) => (
                  <div key={c.label} className="flex items-center gap-3 text-sm">
                    <span className="text-slate-400 w-64 shrink-0">{c.label}</span>
                    <div className="flex-1 h-2 rounded-full bg-black/30 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-brand-500 to-fuchsia-500"
                        style={{ width: `${c.pass_rate}%` }}
                      />
                    </div>
                    <span className="text-slate-300 w-12 text-right">{c.pass_rate.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </section>

        {/* Tabla de estudiantes */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] shadow-lg shadow-black/20 overflow-hidden">
          <h2 className="text-white font-semibold p-5 pb-3">Estudiantes</h2>
          <p className="text-slate-500 text-xs px-5 pb-3 -mt-2">
            Haz clic en un estudiante para ver su código y respuestas por problema.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-black/20 text-slate-400 text-left">
                <tr>
                  <th className="px-5 py-2 font-medium">Nombre</th>
                  <th className="px-5 py-2 font-medium">Correo</th>
                  <th className="px-5 py-2 font-medium">Estado</th>
                  <th className="px-5 py-2 font-medium text-right">Total</th>
                  <th className="px-5 py-2 font-medium text-right">Nota</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {dash.students.map((s) => {
                  const isOpen = expandedId === s.student_id;
                  const detail = detailsById[s.student_id];
                  return (
                    <Fragment key={s.student_id}>
                      <tr
                        onClick={() => toggleStudent(s.student_id)}
                        className="hover:bg-white/[0.03] cursor-pointer select-none"
                      >
                        <td className="px-5 py-2 text-white">
                          <span className="text-slate-500 mr-1.5">{isOpen ? "▾" : "▸"}</span>
                          {s.full_name}
                        </td>
                        <td className="px-5 py-2 text-slate-400">{s.email}</td>
                        <td className="px-5 py-2">
                          {s.annulled ? (
                            <span className="text-xs font-medium rounded-full border px-2.5 py-1 bg-rose-500/15 text-rose-400 border-rose-500/30">
                              Anulado
                            </span>
                          ) : (
                            <span className={`text-xs font-medium rounded-full border px-2.5 py-1 ${STATUS_CLS[s.status]}`}>
                              {STATUS_LABEL[s.status]}
                            </span>
                          )}
                          {s.violations > 0 && (
                            <span className="ml-2 text-xs text-amber-400" title="Salidas de la ventana del examen">
                              ⚠ {s.violations}
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-2 text-right text-slate-300">
                          {s.total_score.toFixed(1)} / {s.max_score.toFixed(0)}
                        </td>
                        <td className="px-5 py-2 text-right font-semibold text-brand-300">{s.nota_5.toFixed(2)}</td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={5} className="bg-black/20 px-5 py-4">
                            {loadingId === s.student_id && (
                              <p className="text-slate-500 text-sm">Cargando respuestas...</p>
                            )}
                            {detail?.error && (
                              <p className="text-rose-400 text-sm">No se pudieron cargar las respuestas.</p>
                            )}
                            {detail?.annulled && (
                              <div className="mb-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 flex items-start justify-between gap-4">
                                <p className="text-rose-200/90 text-sm">
                                  <span className="font-semibold text-rose-300">Anulado (nota 0). </span>
                                  {detail.annul_reason} Abajo se muestra el trabajo real, solo para tu revisión.
                                </p>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    reinstate(s.student_id);
                                  }}
                                  className="shrink-0 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/5 transition"
                                >
                                  Reactivar intento
                                </button>
                              </div>
                            )}
                            {detail && !detail.error && (
                              <div className="space-y-3">
                                {detail.problems.map((p) => (
                                  <div
                                    key={p.problem_id}
                                    className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden"
                                  >
                                    <div className="flex items-center justify-between px-4 py-2 bg-white/[0.03]">
                                      <span className="text-white text-sm font-medium">{p.title}</span>
                                      <span className="text-xs text-slate-400">
                                        {p.score.toFixed(1)} / {p.max_score.toFixed(0)}
                                      </span>
                                    </div>
                                    {p.code ? (
                                      <>
                                        <pre className="text-xs text-slate-200 font-mono whitespace-pre-wrap bg-black/40 px-4 py-3 overflow-x-auto max-h-64 overflow-y-auto">
                                          {p.code}
                                        </pre>
                                        {(p.stdout || p.stderr) && (
                                          <div className="border-t border-white/10 px-4 py-2 bg-black/30">
                                            {p.stdout && (
                                              <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap">
                                                {p.stdout}
                                              </pre>
                                            )}
                                            {p.stderr && (
                                              <pre className="text-xs text-rose-400 font-mono whitespace-pre-wrap mt-1">
                                                {p.stderr}
                                              </pre>
                                            )}
                                          </div>
                                        )}
                                        <div className="px-4 py-2 space-y-1 border-t border-white/10">
                                          {p.checks.map((c, idx) => (
                                            <div key={idx} className="text-xs">
                                              <div className="flex items-center gap-2">
                                                <span className={c.passed ? "text-emerald-400" : "text-rose-400"}>
                                                  {c.passed ? "✓" : "✗"}
                                                </span>
                                                <span className="text-slate-400">
                                                  {c.label} ({c.points}/{c.max_points} pts)
                                                </span>
                                              </div>
                                              {c.feedback && (
                                                <p className="ml-6 mt-0.5 text-slate-500">{c.feedback}</p>
                                              )}
                                            </div>
                                          ))}
                                        </div>
                                      </>
                                    ) : (
                                      <p className="text-slate-500 text-xs px-4 py-3 italic">Sin entrega.</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

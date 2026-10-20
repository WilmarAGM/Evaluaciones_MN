import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import * as api from "../api";

const REVIEW_STATUS = {
  pending: { label: "Solicitud enviada — pendiente de respuesta", cls: "border-amber-500/30 bg-amber-500/10 text-amber-200" },
  accepted: { label: "Solicitud aceptada", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" },
  rejected: { label: "Solicitud rechazada", cls: "border-rose-500/30 bg-rose-500/10 text-rose-200" },
};

function ReviewBox({ examId, problem, onSent }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const review = problem.review;

  if (review) {
    const st = REVIEW_STATUS[review.status] || REVIEW_STATUS.pending;
    return (
      <div className={`mt-4 rounded-lg border px-3 py-2 text-sm ${st.cls}`}>
        <p className="font-medium">{st.label}</p>
        <p className="mt-1 text-xs opacity-80">
          Tu solicitud: <span className="italic">“{review.message}”</span>
        </p>
        {review.response && (
          <p className="mt-1.5 text-xs">
            Respuesta del docente: <span className="font-medium">“{review.response}”</span>
          </p>
        )}
      </div>
    );
  }

  async function handleSend(e) {
    e.preventDefault();
    if (!message.trim()) {
      setError("Explica brevemente por qué debería revisarse tu nota.");
      return;
    }
    setSending(true);
    setError("");
    try {
      const created = await api.requestReview(examId, problem.problem_id, message.trim());
      onSent(problem.problem_id, created);
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo enviar la solicitud.");
    } finally {
      setSending(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="mt-4 text-xs font-medium rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20 px-3 py-1.5 transition"
      >
        Solicitar revisión
      </button>
    );
  }

  return (
    <form onSubmit={handleSend} className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
      <label className="block text-xs text-slate-400 mb-1.5">
        Explica brevemente por qué debería corregirse la nota de este ejercicio (solo puedes enviar una solicitud).
      </label>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        maxLength={2000}
        rows={4}
        autoFocus
        className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
      />
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-[11px] text-slate-600">{message.length}/2000</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              setError("");
            }}
            className="text-xs rounded-lg border border-white/15 px-3 py-1.5 text-slate-300 hover:bg-white/5 transition"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={sending}
            className="text-xs font-medium rounded-lg bg-brand-600/80 hover:bg-brand-600 text-white px-3 py-1.5 transition disabled:opacity-60"
          >
            {sending ? "Enviando..." : "Enviar solicitud"}
          </button>
        </div>
      </div>
      {error && <p className="text-rose-400 text-xs mt-2">{error}</p>}
    </form>
  );
}

export default function ResultsPage() {
  const { examId } = useParams();
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState({});
  const navigate = useNavigate();

  function toggle(problemId) {
    setExpanded((prev) => ({ ...prev, [problemId]: !prev[problemId] }));
  }

  useEffect(() => {
    api
      .getExamResults(examId)
      .then(setResults)
      .catch((err) => {
        if (err.response?.status === 403) {
          navigate(`/exams/${examId}`, { replace: true });
        } else {
          setError("No se pudieron cargar los resultados.");
        }
      });
  }, [examId]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center text-rose-400">{error}</div>
    );
  }

  if (!results) {
    return (
      <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center text-slate-400">
        Cargando resultados...
      </div>
    );
  }

  const percentage = results.max_score > 0 ? (results.total_score / results.max_score) * 100 : 0;

  function handleReviewSent(problemId, review) {
    setResults((prev) => ({
      ...prev,
      problems: prev.problems.map((p) => (p.problem_id === problemId ? { ...p, review } : p)),
    }));
  }

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <Link to="/exams" className="text-slate-400 hover:text-white text-sm">
            ← Exámenes
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {results.annulled && (
          <div className="mb-8 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-5">
            <p className="text-rose-300 font-semibold">Examen anulado — calificación 0</p>
            <p className="text-rose-200/80 text-sm mt-1">{results.annul_reason}</p>
            <p className="text-slate-400 text-xs mt-2">
              Si crees que se trata de un error, comunícate con tu docente.
            </p>
          </div>
        )}

        {!results.review_open ? (
          <div className="text-center rounded-2xl border border-white/10 bg-white/[0.03] p-8">
            <p className="text-slate-400 text-sm">{results.exam_title}</p>
            <h1 className="text-2xl font-bold text-white mt-2">Examen entregado</h1>
            <p className="text-slate-400 mt-3 text-sm">
              Tu docente aún no ha habilitado la revisión. Cuando lo haga, aquí podrás ver tu calificación, tus
              respuestas y solicitar revisión si lo consideras necesario.
            </p>
          </div>
        ) : (
          <>
            <div className="text-center mb-10">
              <p className="text-slate-400 text-sm">{results.exam_title}</p>
              <h1 className="text-4xl font-bold text-white mt-2">
                {results.total_score.toFixed(1)} / {results.max_score}
              </h1>
              <p
                className={`mt-1 font-medium ${
                  percentage >= 60 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {percentage.toFixed(0)}%
              </p>
            </div>

            <div className="space-y-4">
              {results.problems.map((p) => (
                <div
                  key={p.problem_id}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-lg shadow-black/20"
                >
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-white font-semibold">{p.title}</h2>
                    <span className="text-sm font-medium text-slate-300">
                      {p.score.toFixed(1)} / {p.max_score}
                    </span>
                  </div>
                  {p.statement_md && (
                    <details className="mb-3 rounded-xl border border-white/10 bg-black/20">
                      <summary className="cursor-pointer select-none px-4 py-2 text-xs font-medium text-brand-300 hover:text-brand-200">
                        Ver enunciado
                      </summary>
                      <div className="markdown-body px-4 pb-4 text-sm">
                        <ReactMarkdown remarkPlugins={[remarkMath, remarkGfm]} rehypePlugins={[rehypeKatex]}>
                          {p.statement_md}
                        </ReactMarkdown>
                      </div>
                    </details>
                  )}
                  {p.manual && (
                    <p className="mb-3 rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-sm text-sky-200/90">
                      Nota corregida por el docente (calificación automática: {p.auto_score?.toFixed(1)}).
                      {p.manual_comment && <span className="block mt-1 text-sky-100">“{p.manual_comment}”</span>}
                    </p>
                  )}

                  {p.checks.map((check, idx) => (
                    <div key={idx} className="text-sm py-0.5">
                      <div className="flex items-center gap-2">
                        <span className={check.passed ? "text-emerald-400" : "text-rose-400"}>
                          {check.passed ? "✓" : "✗"}
                        </span>
                        <span className="text-slate-400">
                          {check.label} ({check.points}/{check.max_points} pts)
                        </span>
                      </div>
                      {check.feedback && (
                        <p className="ml-6 mt-0.5 text-xs text-slate-500">{check.feedback}</p>
                      )}
                    </div>
                  ))}

                  {p.code && (
                    <div className="mt-4">
                      <button
                        onClick={() => toggle(p.problem_id)}
                        className="text-xs font-medium text-brand-300 hover:text-brand-200 transition"
                      >
                        {expanded[p.problem_id] ? "▾ Ocultar mi código y salida" : "▸ Ver mi código y salida"}
                      </button>

                      {expanded[p.problem_id] && (
                        <div className="mt-3 rounded-xl overflow-hidden border border-white/10">
                          <div className="px-3 py-1.5 bg-[#1e1e1e] border-b border-black/40 text-xs text-slate-400 font-mono">
                            celda_de_codigo.py (entregado)
                          </div>
                          <pre className="text-xs text-slate-200 font-mono whitespace-pre-wrap bg-black/40 px-4 py-3 overflow-x-auto">
                            {p.code}
                          </pre>
                          {(p.stdout || p.stderr) && (
                            <div className="border-t border-white/10 px-4 py-3 bg-black/30">
                              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1.5">Salida</p>
                              {p.stdout && (
                                <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap">{p.stdout}</pre>
                              )}
                              {p.stderr && (
                                <pre className="text-xs text-rose-400 font-mono whitespace-pre-wrap mt-1">{p.stderr}</pre>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  <ReviewBox examId={examId} problem={p} onSent={handleReviewSent} />
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

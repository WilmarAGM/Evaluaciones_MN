import { useEffect, useRef, useState } from "react";
import * as api from "../api";

const STATUS = {
  pending: { label: "Pendiente", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  accepted: { label: "Aceptada", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  rejected: { label: "Rechazada", cls: "bg-rose-500/15 text-rose-300 border-rose-500/30" },
};

function formatDate(iso) {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" });
}

function PendingForm({ request, onResolved }) {
  const [score, setScore] = useState(String(request.score));
  const [response, setResponse] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function resolve(accept) {
    setError("");
    if (!response.trim()) {
      setError("Escribe una respuesta para el estudiante.");
      return;
    }
    const value = Number(score.replace(",", "."));
    if (accept && (score.trim() === "" || Number.isNaN(value))) {
      setError("Escribe la nueva nota del ejercicio.");
      return;
    }
    setBusy(true);
    try {
      const updated = await api.resolveReviewRequest(request.id, {
        accept,
        score: accept ? value : null,
        response: response.trim(),
      });
      onResolved(updated);
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo responder la solicitud.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-2">
      <textarea
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        rows={2}
        placeholder="Respuesta para el estudiante (la verá en su revisión)"
        className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm placeholder:text-slate-500 focus:outline-none focus:border-brand-400/50"
      />
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs text-slate-400">Nueva nota</label>
        <input
          value={score}
          onChange={(e) => setScore(e.target.value)}
          inputMode="decimal"
          className="w-20 rounded-lg bg-black/30 border border-white/10 text-white px-2 py-1 text-sm focus:outline-none focus:border-brand-400/50"
        />
        <span className="text-xs text-slate-500">/ {request.max_score}</span>
        <button
          onClick={() => resolve(true)}
          disabled={busy}
          className="ml-auto text-xs font-medium rounded-lg bg-emerald-600/80 hover:bg-emerald-600 text-white px-3 py-1.5 transition disabled:opacity-60"
        >
          Aceptar y poner nota
        </button>
        <button
          onClick={() => resolve(false)}
          disabled={busy}
          className="text-xs font-medium rounded-lg border border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 px-3 py-1.5 transition disabled:opacity-60"
        >
          Rechazar
        </button>
      </div>
      {error && <p className="text-rose-400 text-xs">{error}</p>}
    </div>
  );
}

export default function ReviewRequestsPanel({ examId, reviewOpen, onChange, onOpenStudent }) {
  const [requests, setRequests] = useState(null);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    api
      .getReviewRequests(examId)
      .then((data) => {
        setRequests(data);
        if (window.location.hash === "#revisiones") {
          setTimeout(() => ref.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
        }
      })
      .catch(() => setError("No se pudieron cargar las solicitudes de revisión."));
  }, [examId]);

  async function handleToggle() {
    if (
      !reviewOpen &&
      !window.confirm(
        "¿Habilitar la revisión? Los estudiantes que ya terminaron verán su nota, sus respuestas y los criterios, y podrán solicitar revisión de cada ejercicio."
      )
    )
      return;
    setToggling(true);
    try {
      await api.toggleExamReview(examId);
      await onChange();
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo cambiar la revisión.");
    } finally {
      setToggling(false);
    }
  }

  function handleResolved(updated) {
    setRequests((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    onChange(updated.student_id);
  }

  const pending = requests?.filter((r) => r.status === "pending").length || 0;

  return (
    <section
      id="revisiones"
      ref={ref}
      className="scroll-mt-24 rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-lg shadow-black/20 space-y-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-white font-semibold flex items-center gap-2">
            Revisión
            {pending > 0 && (
              <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1.5 text-xs font-bold text-black">
                {pending}
              </span>
            )}
          </h2>
          <p className="text-slate-500 text-xs mt-1">
            {reviewOpen
              ? "Habilitada: quienes terminaron ven su nota, respuestas y criterios, y pueden solicitar revisión."
              : "Cerrada: los estudiantes solo ven \"Examen entregado\", sin nota."}
          </p>
        </div>
        <button
          type="button"
          onClick={handleToggle}
          disabled={toggling}
          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium transition disabled:opacity-60 ${
            reviewOpen
              ? "border-white/15 text-slate-200 hover:bg-white/5"
              : "border-sky-500/40 bg-sky-500/15 text-sky-300 hover:bg-sky-500/25"
          }`}
        >
          {toggling ? "Actualizando..." : reviewOpen ? "Cerrar revisión" : "📝 Habilitar revisión"}
        </button>
      </div>

      {error && <p className="text-rose-400 text-sm">{error}</p>}

      {requests && requests.length === 0 && (
        <p className="text-slate-500 text-sm">Aún no hay solicitudes de revisión.</p>
      )}

      {requests && requests.length > 0 && (
        <ul className="space-y-3">
          {requests.map((r) => {
            const st = STATUS[r.status] || STATUS.pending;
            return (
              <li key={r.id} className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => onOpenStudent(r.student_id)}
                    className="text-white font-medium hover:text-brand-300 transition"
                    title="Ver sus respuestas en la tabla de estudiantes"
                  >
                    {r.student_name || r.student_email}
                  </button>
                  <span className="text-slate-500 text-sm">· {r.problem_title}</span>
                  <span className={`text-xs font-medium rounded-full border px-2 py-0.5 ${st.cls}`}>{st.label}</span>
                  <span className="ml-auto text-xs text-slate-500">
                    Nota actual: <span className="text-slate-200">{r.score.toFixed(1)}</span> / {r.max_score}
                    {r.manual && ` (automática ${r.auto_score.toFixed(1)})`}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-300 whitespace-pre-wrap">“{r.message}”</p>
                <p className="mt-1 text-[11px] text-slate-600">Enviada {formatDate(r.created_at)}</p>
                {r.status === "pending" ? (
                  <PendingForm request={r} onResolved={handleResolved} />
                ) : (
                  <p className="mt-2 text-xs text-slate-400">
                    Tu respuesta: <span className="text-slate-200">“{r.response}”</span>
                    {r.resolved_at && <span className="text-slate-600"> · {formatDate(r.resolved_at)}</span>}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

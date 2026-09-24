import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import { useAuth } from "../AuthContext";
import * as api from "../api";

const CHECK_TYPE_LABELS = {
  final_value: "Valor final",
  call: "Llamada a función",
  function: "Función equivalente",
};

function CheckRow({ check }) {
  return (
    <li className="rounded-lg border border-white/10 bg-black/20 px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-slate-200">{check.label}</span>
        <span className="text-xs text-slate-500 shrink-0">{check.points} pts</span>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xs font-medium rounded-full border px-2 py-0.5 bg-brand-500/10 text-brand-300 border-brand-500/30">
          {CHECK_TYPE_LABELS[check.type] || check.type}
        </span>
        {check.type === "final_value" && (
          <span className="text-xs text-slate-500">
            {check.variable} ≈ {check.expected} (± {check.tolerance})
          </span>
        )}
        {check.type === "call" && (
          <span className="text-xs text-slate-500 font-mono">{(check.qualnames || []).join(", ")}</span>
        )}
      </div>
    </li>
  );
}

// Igual que TeacherProblemDetail, pero sobre un problema de un banco
// GENERAL (ver AdminBanks.jsx) — el admin sí puede publicar/eliminar aquí,
// a diferencia de la vista de solo lectura que ve un docente.
export default function AdminProblemDetail() {
  const { problemId } = useParams();
  const [problem, setProblem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    api
      .getAdminProblemDetail(problemId)
      .then(setProblem)
      .catch(() => setError("No se pudo cargar el problema."))
      .finally(() => setLoading(false));
  }, [problemId]);

  async function handlePublish() {
    setPublishing(true);
    try {
      await api.publishAdminProblem(problem.id);
      setProblem((prev) => ({ ...prev, status: "published" }));
    } catch (err) {
      window.alert("No se pudo publicar el problema.");
    } finally {
      setPublishing(false);
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm(`¿Eliminar el problema "${problem.title}"? Esta acción no se puede deshacer.`);
    if (!confirmed) return;

    setDeleting(true);
    try {
      await api.deleteAdminProblem(problem.id);
      navigate("/admin/banks");
    } catch (err) {
      window.alert(err.response?.data?.detail || "No se pudo eliminar el problema.");
      setDeleting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-fuchsia-500 flex items-center justify-center text-white font-bold">
              ∑
            </div>
            <span className="text-white font-semibold">Métodos Numéricos · Admin</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm hidden sm:block">{user?.full_name || user?.email}</span>
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

      <main className="max-w-4xl mx-auto px-6 py-10">
        <Link to="/admin/banks" className="text-sm text-slate-400 hover:text-white transition">
          ← Volver a bancos generales
        </Link>

        {loading && <p className="text-slate-500 mt-6">Cargando...</p>}
        {error && <p className="text-rose-400 mt-6">{error}</p>}

        {problem && (
          <div className="mt-4">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <p className="text-slate-500 text-sm">{problem.bank_title}</p>
                <h1 className="text-2xl font-bold text-white mt-1">{problem.title}</h1>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`text-xs font-medium rounded-full border px-2.5 py-1 ${
                    problem.status === "draft"
                      ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                      : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                  }`}
                >
                  {problem.status === "draft" ? "Borrador" : "Publicado"}
                </span>
                <span className="text-xs text-slate-500 rounded-full border border-white/10 px-2.5 py-1">
                  {problem.max_score.toFixed(0)} pts
                </span>
                {problem.status === "draft" && (
                  <button
                    onClick={handlePublish}
                    disabled={publishing}
                    className="text-xs font-medium rounded-lg border border-emerald-500/30 bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 px-3 py-1.5 transition disabled:opacity-60"
                  >
                    {publishing ? "Publicando..." : "Publicar"}
                  </button>
                )}
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="text-xs font-medium rounded-lg border border-red-900/50 bg-red-950/40 text-red-400 hover:bg-red-900/40 hover:text-red-300 px-3 py-1.5 transition disabled:opacity-60"
                >
                  {deleting ? "Eliminando..." : "🗑 Eliminar"}
                </button>
              </div>
            </div>

            {problem.review_notes && (
              <pre className="mt-4 text-sm text-rose-300/90 bg-rose-950/20 border border-rose-900/30 rounded-xl px-4 py-3 whitespace-pre-wrap font-sans">
                {problem.review_notes}
              </pre>
            )}

            <section className="mt-6 rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
              <div className="px-6 py-3 border-b border-white/10 bg-white/[0.02]">
                <p className="text-xs uppercase tracking-wide text-slate-500">Enunciado</p>
              </div>
              <div className="markdown-body px-6 py-5">
                <ReactMarkdown remarkPlugins={[remarkMath, remarkGfm]} rehypePlugins={[rehypeKatex]}>
                  {problem.statement_md}
                </ReactMarkdown>
              </div>
            </section>

            <section className="mt-6 rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
              <div className="px-6 py-3 border-b border-white/10 bg-white/[0.02]">
                <p className="text-xs uppercase tracking-wide text-slate-500">Código inicial (starter_code)</p>
              </div>
              <pre className="px-6 py-4 bg-black/40 text-sm text-slate-200 font-mono whitespace-pre-wrap overflow-x-auto">
                {problem.starter_code}
              </pre>
            </section>

            {problem.solution_code && (
              <section className="mt-6 rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
                <div className="px-6 py-3 border-b border-white/10 bg-white/[0.02]">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Solución de referencia</p>
                </div>
                <pre className="px-6 py-4 bg-black/40 text-sm text-slate-200 font-mono whitespace-pre-wrap overflow-x-auto">
                  {problem.solution_code}
                </pre>
              </section>
            )}

            <section className="mt-6 rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
              <div className="px-6 py-3 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
                <p className="text-xs uppercase tracking-wide text-slate-500">Rúbrica</p>
                <span className="text-xs text-slate-500">{problem.rubric.length} chequeo(s)</span>
              </div>
              <ul className="px-6 py-4 space-y-2">
                {problem.rubric.map((check) => (
                  <CheckRow key={check.id} check={check} />
                ))}
              </ul>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import * as api from "../api";

function BankTexUploader({ bank, onLoaded }) {
  const [file, setFile] = useState(null);
  const [maxProblems, setMaxProblems] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Elige un archivo .tex primero.");
      return;
    }
    setError("");
    setResult(null);
    setUploading(true);
    try {
      const res = await api.loadBankFromTex(bank.id, file, maxProblems ? Number(maxProblems) : undefined);
      setResult(res);
      onLoaded(bank.id, res.created);
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo cargar el archivo.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-dashed border-white/10 bg-black/20 p-3">
      <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2">
        <input
          type="file"
          accept=".tex"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-xs text-slate-300 file:mr-2 file:rounded-lg file:border-0 file:bg-white/10 file:px-2.5 file:py-1.5 file:text-xs file:text-slate-200 file:cursor-pointer max-w-[220px]"
        />
        <input
          type="number"
          min="1"
          value={maxProblems}
          onChange={(e) => setMaxProblems(e.target.value)}
          placeholder="máx. problemas"
          className="w-28 rounded-lg bg-black/30 border border-white/10 text-white px-2 py-1.5 text-xs focus:outline-none focus:border-brand-400/50"
        />
        <button
          type="submit"
          disabled={uploading}
          className="text-xs font-medium rounded-lg border border-brand-500/30 bg-brand-600/20 text-brand-300 hover:bg-brand-600/30 px-3 py-1.5 transition disabled:opacity-60"
        >
          {uploading ? "🤖 Generando..." : "🤖 Cargar con IA"}
        </button>
      </form>
      {uploading && (
        <p className="text-xs text-slate-500 mt-2">
          Corriendo el pipeline de agentes (parsear, resolver, armar y auditar rúbrica)... puede tardar
          varios minutos. No cierres esta pestaña.
        </p>
      )}
      {error && <p className="text-xs text-rose-400 mt-2">{error}</p>}
      {result && (
        <>
          <p className="text-xs text-emerald-400 mt-2">
            {result.created.length} problema(s) creado(s) como borrador
            {result.skipped.length > 0 && `, ${result.skipped.length} omitido(s)`}. Cupo Gemini hoy:{" "}
            {result.calls_today} llamados, {result.tokens_today} tokens.
          </p>
          {result.skipped.length > 0 && (
            <ul className="mt-1.5 space-y-1">
              {result.skipped.map((s, i) => (
                <li key={i} className="text-xs text-amber-400/90">
                  <span className="font-medium">{s.title}:</span> {s.reason}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

export default function TeacherBanks() {
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [publishingId, setPublishingId] = useState(null);
  const [deletingProblemId, setDeletingProblemId] = useState(null);
  const [deletingBankId, setDeletingBankId] = useState(null);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadBanks();
  }, []);

  function loadBanks() {
    setLoading(true);
    return api
      .getTeacherBanks()
      .then(setBanks)
      .catch(() => setError("No se pudieron cargar los bancos de problemas."))
      .finally(() => setLoading(false));
  }

  async function handlePublish(problemId) {
    setPublishingId(problemId);
    try {
      await api.publishTeacherProblem(problemId);
      setBanks((prev) =>
        prev.map((bank) => ({
          ...bank,
          problems: bank.problems.map((p) => (p.id === problemId ? { ...p, status: "published" } : p)),
        }))
      );
    } catch (err) {
      window.alert("No se pudo publicar el problema.");
    } finally {
      setPublishingId(null);
    }
  }

  async function handleDeleteProblem(problem) {
    const confirmed = window.confirm(`¿Eliminar el problema "${problem.title}"? Esta acción no se puede deshacer.`);
    if (!confirmed) return;

    setDeletingProblemId(problem.id);
    try {
      await api.deleteTeacherProblem(problem.id);
      setBanks((prev) =>
        prev.map((bank) => ({ ...bank, problems: bank.problems.filter((p) => p.id !== problem.id) }))
      );
    } catch (err) {
      window.alert(err.response?.data?.detail || "No se pudo eliminar el problema.");
    } finally {
      setDeletingProblemId(null);
    }
  }

  async function handleDeleteBank(bank) {
    const confirmed = window.confirm(
      `¿Eliminar el banco "${bank.title}" completo, con sus ${bank.problems.length} problema(s)? Esta acción no se puede deshacer.`
    );
    if (!confirmed) return;

    setDeletingBankId(bank.id);
    try {
      await api.deleteTeacherBank(bank.id);
      setBanks((prev) => prev.filter((b) => b.id !== bank.id));
    } catch (err) {
      window.alert(err.response?.data?.detail || "No se pudo eliminar el banco.");
    } finally {
      setDeletingBankId(null);
    }
  }

  function handleTexLoaded(bankId, created) {
    if (!created.length) return;
    setBanks((prev) =>
      prev.map((bank) =>
        bank.id === bankId
          ? { ...bank, problems: [...bank.problems, ...created.map((p) => ({ ...p, status: "draft" }))] }
          : bank
      )
    );
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    if (!title.trim()) {
      setError("El banco necesita un título.");
      return;
    }
    setCreating(true);
    try {
      const bank = await api.createTeacherBank({ title: title.trim(), description: description.trim() || null });
      setBanks((prev) => [...prev, bank]);
      setTitle("");
      setDescription("");
    } catch (err) {
      setError("No se pudo crear el banco. Intenta de nuevo.");
    } finally {
      setCreating(false);
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
          <h1 className="text-2xl font-bold text-white">Bancos de problemas</h1>
          <Link
            to="/teacher/exams"
            className="shrink-0 rounded-lg border border-white/10 hover:bg-white/5 text-slate-200 text-sm font-medium px-4 py-2 transition"
          >
            ← Volver a exámenes
          </Link>
        </div>
        <p className="text-slate-400 mb-8">
          Colecciones de problemas reutilizables para armar exámenes (fijos o sorteados aleatoriamente).
        </p>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-5 mb-10">
          <h2 className="text-lg font-semibold text-white mb-4">Crear banco nuevo</h2>
          <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Título</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ej. Raíces de ecuaciones"
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Descripción (opcional)</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Notas sobre el contenido del banco"
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              />
            </div>
            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-brand-600/80 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 transition disabled:opacity-60"
            >
              {creating ? "Creando..." : "+ Crear banco"}
            </button>
          </form>
          {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}

          <div className="mt-5 rounded-xl border border-dashed border-white/10 bg-black/20 p-4">
            <p className="text-sm text-slate-300 font-medium">🤖 Cargue asistido con agentes IA (Gemini)</p>
            <p className="text-sm text-slate-500 mt-1">
              Ya disponible: crea el banco arriba y luego usa "🤖 Cargar con IA" en su tarjeta para subir un
              .tex y generar problemas automáticamente (quedan como borrador, revísalos antes de publicar).
            </p>
          </div>
        </section>

        {loading && <p className="text-slate-500">Cargando...</p>}

        <div className="grid gap-4 sm:grid-cols-2">
          {banks.map((bank) => (
            <div
              key={bank.id}
              className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-lg shadow-black/20"
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-lg font-semibold text-white">{bank.title}</h3>
                <button
                  onClick={() => handleDeleteBank(bank)}
                  disabled={deletingBankId === bank.id}
                  title="Eliminar banco completo"
                  className="shrink-0 text-xs font-medium rounded-lg border border-red-900/50 bg-red-950/40 text-red-400 hover:bg-red-900/40 hover:text-red-300 px-2 py-1 transition disabled:opacity-60"
                >
                  {deletingBankId === bank.id ? "..." : "🗑 Eliminar banco"}
                </button>
              </div>
              {bank.description && <p className="text-slate-400 text-sm mt-1">{bank.description}</p>}

              <p className="text-slate-500 text-xs mt-3 mb-2">
                {bank.problems.length} problema{bank.problems.length === 1 ? "" : "s"}
              </p>
              {bank.problems.length > 0 && (
                <ul className="space-y-1.5">
                  {bank.problems.map((p) => (
                    <li key={p.id} className="text-sm text-slate-300">
                      <div className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-2 min-w-0">
                          <Link to={`/teacher/problems/${p.id}`} className="truncate hover:text-brand-300 hover:underline transition">
                            {p.title}
                          </Link>
                          {p.status === "draft" && (
                            <span className="shrink-0 text-xs font-medium rounded-full border px-2 py-0.5 bg-amber-500/15 text-amber-400 border-amber-500/30">
                              Borrador
                            </span>
                          )}
                          {p.review_notes && (
                            <span className="shrink-0 text-xs font-medium rounded-full border px-2 py-0.5 bg-rose-500/15 text-rose-400 border-rose-500/30">
                              ⚠ Revisar
                            </span>
                          )}
                        </span>
                        <span className="flex items-center gap-2 shrink-0">
                          <span className="text-slate-500">{p.max_score.toFixed(0)} pts</span>
                          {p.status === "draft" && (
                            <button
                              onClick={() => handlePublish(p.id)}
                              disabled={publishingId === p.id}
                              className="text-xs font-medium rounded-lg border border-emerald-500/30 bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 px-2 py-1 transition disabled:opacity-60"
                            >
                              {publishingId === p.id ? "..." : "Publicar"}
                            </button>
                          )}
                          <button
                            onClick={() => handleDeleteProblem(p)}
                            disabled={deletingProblemId === p.id}
                            title="Eliminar problema"
                            className="text-xs font-medium rounded-lg border border-red-900/50 bg-red-950/40 text-red-400 hover:bg-red-900/40 hover:text-red-300 px-2 py-1 transition disabled:opacity-60"
                          >
                            {deletingProblemId === p.id ? "..." : "🗑"}
                          </button>
                        </span>
                      </div>
                      {p.review_notes && (
                        <pre className="mt-1 text-xs text-rose-300/90 bg-rose-950/20 border border-rose-900/30 rounded-lg px-2.5 py-2 whitespace-pre-wrap font-sans">
                          {p.review_notes}
                        </pre>
                      )}
                    </li>
                  ))}
                </ul>
              )}

              <BankTexUploader bank={bank} onLoaded={handleTexLoaded} />
            </div>
          ))}
        </div>

        {!loading && banks.length === 0 && (
          <p className="text-slate-500">No hay bancos de problemas todavía.</p>
        )}
      </main>
    </div>
  );
}

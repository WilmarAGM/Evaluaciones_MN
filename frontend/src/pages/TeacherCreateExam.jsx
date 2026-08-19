import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import * as api from "../api";

let nextRowId = 1;

function emptyRow() {
  return { id: nextRowId++, mode: "random", bankId: "", count: 1, problemId: "" };
}

export default function TeacherCreateExam() {
  const [banks, setBanks] = useState([]);
  const [loadingBanks, setLoadingBanks] = useState(true);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [untimed, setUntimed] = useState(false);
  const [durationMinutes, setDurationMinutes] = useState(50);
  const [rows, setRows] = useState([emptyRow()]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .getTeacherBanks({ publishedOnly: true })
      .then(setBanks)
      .catch(() => setError("No se pudieron cargar los bancos de problemas."))
      .finally(() => setLoadingBanks(false));
  }, []);

  function updateRow(id, patch) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  function addRow() {
    setRows((prev) => [...prev, emptyRow()]);
  }

  function removeRow(id) {
    setRows((prev) => (prev.length > 1 ? prev.filter((r) => r.id !== id) : prev));
  }

  function bankOf(bankId) {
    return banks.find((b) => String(b.id) === String(bankId));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("El examen necesita un título.");
      return;
    }
    if (rows.length === 0) {
      setError("Agrega al menos un ejercicio.");
      return;
    }

    const slots = [];
    for (const row of rows) {
      if (!row.bankId) {
        setError("Selecciona un banco para cada ejercicio.");
        return;
      }
      const bank = bankOf(row.bankId);
      if (row.mode === "fixed") {
        if (!row.problemId) {
          setError("Elige un problema específico para cada ejercicio marcado como 'Específico'.");
          return;
        }
        slots.push({ kind: "fixed", problem_id: Number(row.problemId) });
      } else {
        const count = Number(row.count) || 1;
        if (bank && count > bank.problems.length) {
          setError(`El banco "${bank.title}" solo tiene ${bank.problems.length} problema(s).`);
          return;
        }
        slots.push({ kind: "random", bank_id: Number(row.bankId), count });
      }
    }

    setSubmitting(true);
    try {
      await api.createTeacherExam({
        title: title.trim(),
        description: description.trim() || null,
        duration_minutes: untimed ? null : Number(durationMinutes) || null,
        slots,
      });
      navigate("/teacher/exams");
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo crear el examen.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-fuchsia-500 flex items-center justify-center text-white font-bold">
            ∑
          </div>
          <span className="text-white font-semibold">Crear examen</span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        <Link to="/teacher/exams" className="text-brand-300 hover:text-brand-200 text-sm transition">
          ← Volver a exámenes
        </Link>

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5 space-y-4">
            <div>
              <label className="block text-sm text-slate-300 mb-1">Título</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-400/60"
                placeholder="Ej. Parcial Práctico Tres - Sesión 1"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Descripción (opcional)</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-400/60"
              />
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input
                  type="checkbox"
                  checked={untimed}
                  onChange={(e) => setUntimed(e.target.checked)}
                  className="rounded border-white/20 bg-black/30"
                />
                Sin límite de tiempo
              </label>
              {!untimed && (
                <div className="flex items-center gap-2">
                  <label className="text-sm text-slate-300">Duración (min)</label>
                  <input
                    type="number"
                    min={1}
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(e.target.value)}
                    className="w-24 rounded-lg bg-black/30 border border-white/10 px-3 py-1.5 text-white focus:outline-none focus:border-brand-400/60"
                  />
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-5 space-y-4">
            <h2 className="text-white font-semibold">Ejercicios</h2>

            {loadingBanks && <p className="text-slate-500 text-sm">Cargando bancos...</p>}

            {!loadingBanks &&
              rows.map((row, idx) => {
                const bank = bankOf(row.bankId);
                return (
                  <div key={row.id} className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-300">Ejercicio {idx + 1}</span>
                      {rows.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeRow(row.id)}
                          className="text-xs text-rose-400 hover:text-rose-300 transition"
                        >
                          Quitar
                        </button>
                      )}
                    </div>

                    <div className="grid sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Banco</label>
                        <select
                          value={row.bankId}
                          onChange={(e) => updateRow(row.id, { bankId: e.target.value, problemId: "" })}
                          className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-white focus:outline-none focus:border-brand-400/60"
                        >
                          <option value="">Selecciona un banco...</option>
                          {banks.map((b) => (
                            <option key={b.id} value={b.id}>
                              {b.title} ({b.problems.length} problemas)
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Selección</label>
                        <select
                          value={row.mode}
                          onChange={(e) => updateRow(row.id, { mode: e.target.value })}
                          className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-white focus:outline-none focus:border-brand-400/60"
                        >
                          <option value="random">Aleatorio (sorteo por estudiante)</option>
                          <option value="fixed">Específico (elijo el problema)</option>
                        </select>
                      </div>
                    </div>

                    {row.mode === "random" ? (
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Cantidad a sortear</label>
                        <input
                          type="number"
                          min={1}
                          max={bank ? bank.problems.length : undefined}
                          value={row.count}
                          onChange={(e) => updateRow(row.id, { count: e.target.value })}
                          className="w-24 rounded-lg bg-black/30 border border-white/10 px-3 py-1.5 text-white focus:outline-none focus:border-brand-400/60"
                        />
                        {bank && (
                          <span className="ml-2 text-xs text-slate-500">de {bank.problems.length} disponibles</span>
                        )}
                      </div>
                    ) : (
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Problema</label>
                        <select
                          value={row.problemId}
                          onChange={(e) => updateRow(row.id, { problemId: e.target.value })}
                          className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-white focus:outline-none focus:border-brand-400/60"
                          disabled={!bank}
                        >
                          <option value="">Selecciona un problema...</option>
                          {bank?.problems.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.title}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                );
              })}

            <button
              type="button"
              onClick={addRow}
              className="text-sm text-brand-300 hover:text-brand-200 transition"
            >
              + Agregar ejercicio
            </button>
          </div>

          {error && <p className="text-rose-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={submitting || loadingBanks}
            className="w-full rounded-lg bg-brand-600/80 hover:bg-brand-600 text-white font-medium px-4 py-2.5 transition disabled:opacity-60"
          >
            {submitting ? "Creando..." : "Crear examen (deshabilitado)"}
          </button>
          <p className="text-xs text-slate-500 text-center">
            El examen se crea deshabilitado — habilítalo desde la lista de exámenes cuando estés listo.
          </p>
        </form>
      </main>
    </div>
  );
}

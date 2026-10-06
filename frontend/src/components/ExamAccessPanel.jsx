import { useEffect, useRef, useState } from "react";
import * as api from "../api";

function resultMessage(res) {
  const parts = [];
  if (res.added) parts.push(`${res.added} habilitado(s)`);
  if (res.already) parts.push(`${res.already} ya estaba(n) en la lista`);
  return parts.join(" · ");
}

// Quién puede presentar el examen: todo el grupo (por defecto) o solo una
// lista de documentos, cargada desde Excel o agregada uno a uno en el momento.
export default function ExamAccessPanel({ examId, onChange, initialError = "" }) {
  const [access, setAccess] = useState(null);
  const [documento, setDocumento] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const [notice, setNotice] = useState("");
  const [unknown, setUnknown] = useState([]);
  const fileRef = useRef(null);

  useEffect(() => {
    api
      .getExamAccess(examId)
      .then(setAccess)
      .catch(() => setError("No se pudo cargar la lista de habilitados."));
  }, [examId]);

  async function run(action) {
    setBusy(true);
    setError("");
    setNotice("");
    setUnknown([]);
    try {
      const res = await action();
      setAccess(res);
      setNotice(resultMessage(res));
      setUnknown(res.unknown || []);
      onChange?.();
      return true;
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo completar la operación.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function handleAdd(e) {
    e.preventDefault();
    if (!documento.trim()) return;
    if (await run(() => api.addExamAllowedStudent(examId, documento.trim()))) setDocumento("");
  }

  async function handleFile(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) await run(() => api.importExamAllowedStudents(examId, file));
  }

  function handleToggle() {
    const next = !access.restricted;
    if (next && access.allowed.length === 0) {
      const ok = window.confirm(
        "La lista está vacía: al activar la restricción NADIE podrá empezar el examen hasta que agregues documentos. ¿Continuar?"
      );
      if (!ok) return;
    }
    run(() => api.setExamRestricted(examId, next));
  }

  function handleRemove(entry) {
    const who = entry.full_name || entry.documento;
    if (!window.confirm(`¿Quitar a ${who} de la lista? Si ya empezó el examen, podrá terminarlo.`)) return;
    run(() => api.removeExamAllowedStudent(examId, entry.documento));
  }

  if (!access) {
    return (
      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm text-slate-500">
        {error ? <span className="text-rose-400">{error}</span> : "Cargando habilitados..."}
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-lg shadow-black/20 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-white font-semibold">Quién puede presentarlo</h2>
          <p className="text-slate-500 text-xs mt-1">
            {access.restricted
              ? `Solo los ${access.allowed.length} documento(s) de la lista. Los cambios aplican de inmediato.`
              : "Todo el grupo. Activa la restricción para habilitar solo a ciertos estudiantes."}
          </p>
        </div>
        <button
          type="button"
          onClick={handleToggle}
          disabled={busy}
          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium transition disabled:opacity-60 ${
            access.restricted
              ? "border-amber-500/40 bg-amber-500/15 text-amber-300 hover:bg-amber-500/25"
              : "border-white/15 text-slate-200 hover:bg-white/5"
          }`}
        >
          {access.restricted ? "Restringido — abrir a todo el grupo" : "Restringir a una lista"}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <form onSubmit={handleAdd} className="flex items-center gap-2">
          <input
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            placeholder="Número de documento"
            inputMode="numeric"
            className="w-48 rounded-lg bg-black/30 border border-white/10 px-3 py-1.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-400/60"
          />
          <button
            type="submit"
            disabled={busy || !documento.trim()}
            className="rounded-lg bg-brand-600/80 hover:bg-brand-600 px-3 py-1.5 text-xs font-medium text-white transition disabled:opacity-60"
          >
            Habilitar
          </button>
        </form>
        <span className="text-slate-600 text-xs">o</span>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/5 transition disabled:opacity-60"
        >
          Subir Excel (.xlsx / .xls)
        </button>
        <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
      </div>
      <p className="text-slate-600 text-xs -mt-2">
        Del Excel se lee la columna con encabezado “Documento” (o la primera columna). Subirlo agrega a la lista y
        activa la restricción.
      </p>

      {error && <p className="text-rose-400 text-sm">{error}</p>}
      {notice && <p className="text-emerald-400 text-sm">{notice}</p>}
      {unknown.length > 0 && (
        <p className="text-amber-400 text-sm">
          Sin estudiante en tu grupo (se guardaron igual; revisa que estén bien escritos): {unknown.join(", ")}
        </p>
      )}

      {access.allowed.length > 0 && (
        <div className="max-h-72 overflow-y-auto rounded-xl border border-white/10">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-white/5">
              {access.allowed.map((a) => (
                <tr key={a.documento}>
                  <td className="px-4 py-1.5 font-mono text-slate-300">{a.documento}</td>
                  <td className="px-4 py-1.5">
                    {a.student_id ? (
                      <span className="text-white">{a.full_name || a.email}</span>
                    ) : (
                      <span className="text-amber-400 text-xs">No corresponde a ningún estudiante del grupo</span>
                    )}
                  </td>
                  <td className="px-4 py-1.5 text-right">
                    <button
                      type="button"
                      onClick={() => handleRemove(a)}
                      disabled={busy}
                      className="text-xs text-rose-400 hover:text-rose-300 transition disabled:opacity-60"
                    >
                      Quitar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

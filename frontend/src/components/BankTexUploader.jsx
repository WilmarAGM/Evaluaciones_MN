import { useEffect, useState } from "react";
import * as api from "../api";

const LOAD_JOB_POLL_MS = 4000;
const loadJobStorageKey = (scope, bankId) => `load_tex_job_${scope}_${bankId}`;

// Compartido entre TeacherBanks (bancos de grupo) y AdminBanks (bancos
// generales): sube un .tex y sondea el job en segundo plano hasta que
// termine. `scope` ("teacher" | "admin") solo se usa para namespacing de la
// clave en localStorage, en caso de que un mismo navegador use ambas
// sesiones (poco probable, pero gratis evitar la colisión).
export default function BankTexUploader({ bank, onLoaded, uploadFn, scope = "teacher" }) {
  const [file, setFile] = useState(null);
  const [maxProblems, setMaxProblems] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // Sondea el estado del trabajo hasta que deje de estar "running" — el
  // pipeline corre en segundo plano en el servidor (ver main.py), puede
  // tardar varios minutos con varios numerales. El job_id se guarda en
  // localStorage (no solo en memoria) para que, si se recarga la página por
  // impaciencia -como pasó en producción antes de este cambio, cuando la
  // conexión se cortaba y parecía un error aunque el pipeline seguía
  // trabajando bien del otro lado-, retome el sondeo en vez de perder de
  // vista el progreso.
  async function pollJob(jobId) {
    try {
      localStorage.setItem(loadJobStorageKey(scope, bank.id), jobId);
    } catch {
      /* localStorage no disponible: el sondeo igual funciona, solo no sobrevive un recargo */
    }
    for (;;) {
      await new Promise((resolve) => setTimeout(resolve, LOAD_JOB_POLL_MS));
      let job;
      try {
        job = await api.getLoadTexJobStatus(jobId);
      } catch (err) {
        setError(err.response?.data?.detail || "Se perdió la conexión con el trabajo de carga.");
        break;
      }
      if (job.status === "running") continue;
      if (job.status === "error") {
        setError(job.error || "No se pudo cargar el archivo.");
      } else {
        setResult(job.result);
        onLoaded(bank.id, job.result.created);
      }
      break;
    }
    try {
      localStorage.removeItem(loadJobStorageKey(scope, bank.id));
    } catch {
      /* nada que limpiar si no hay localStorage */
    }
  }

  // Al montar (incluida una recarga de página), retoma el sondeo de un
  // trabajo que haya quedado a medias para este banco.
  useEffect(() => {
    let savedJobId = null;
    try {
      savedJobId = localStorage.getItem(loadJobStorageKey(scope, bank.id));
    } catch {
      /* sin localStorage, no hay nada que retomar */
    }
    if (savedJobId) {
      setUploading(true);
      pollJob(savedJobId).finally(() => setUploading(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bank.id]);

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
      const { job_id } = await uploadFn(bank.id, file, maxProblems ? Number(maxProblems) : undefined);
      await pollJob(job_id);
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
          varios minutos. El trabajo sigue en el servidor aunque cierres o recargues esta página; al
          volver a esta pantalla retoma el progreso solo.
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

import { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import * as api from "../api";
import { registerPythonCompletions } from "../monacoPython";

const DRAFT_SAVE_DEBOUNCE_MS = 1500;

export default function ProblemCard({
  problem,
  index,
  examFinished,
  hideGrading = false,
  runFn = api.runCode,
  saveFn = api.saveCode,
  draftSaveFn = api.saveDraft,
}) {
  const [code, setCode] = useState(problem.starter_code);
  const [output, setOutput] = useState(null);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [canSave, setCanSave] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [loadingSaved, setLoadingSaved] = useState(true);
  // Autoguardado del texto tal cual se escribe (independiente de "Ejecutar"/
  // "Guardar respuesta"), para no perder lo tecleado si el estudiante nunca
  // llega a pulsar esos botones (se acaba el tiempo, se cae la conexión, etc.).
  const [draftState, setDraftState] = useState("idle"); // idle | pending | saving | saved | error
  const draftTimerRef = useRef(null);
  const latestCodeRef = useRef(problem.starter_code);

  useEffect(() => {
    api
      .getMySubmission(problem.id)
      .then((saved) => {
        if (saved) {
          setCode(saved.code);
          latestCodeRef.current = saved.code;
          setOutput({ stdout: saved.stdout, stderr: saved.stderr });
          setSavedAt(saved.saved_at);
        }
      })
      .finally(() => setLoadingSaved(false));
  }, [problem.id]);

  function flushDraft() {
    if (draftTimerRef.current) {
      clearTimeout(draftTimerRef.current);
      draftTimerRef.current = null;
    }
    setDraftState("saving");
    draftSaveFn(problem.id, latestCodeRef.current)
      .then(() => setDraftState("saved"))
      .catch(() => setDraftState("error"));
  }

  useEffect(() => {
    // Última red de seguridad: si el estudiante cambia de pestaña, minimiza,
    // o cierra/recarga con un autoguardado todavía pendiente (dentro de la
    // ventana de debounce), lo mandamos ya en vez de esperar el timer.
    function handleVisibility() {
      if (document.visibilityState === "hidden" && draftTimerRef.current) {
        flushDraft();
      }
    }
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("beforeunload", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("beforeunload", handleVisibility);
      if (draftTimerRef.current) clearTimeout(draftTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problem.id]);

  function scheduleDraftSave(nextCode) {
    latestCodeRef.current = nextCode;
    setDraftState("pending");
    if (draftTimerRef.current) clearTimeout(draftTimerRef.current);
    draftTimerRef.current = setTimeout(flushDraft, DRAFT_SAVE_DEBOUNCE_MS);
  }

  async function handleRun() {
    setRunning(true);
    setOutput(null);
    setCanSave(false);
    try {
      const result = await runFn(problem.id, code);
      setOutput(result);
      setCanSave(true);
      // El backend ya persistió código + resultado al ejecutar; cancelamos
      // cualquier autoguardado pendiente de un código más viejo.
      if (draftTimerRef.current) {
        clearTimeout(draftTimerRef.current);
        draftTimerRef.current = null;
      }
      setSavedAt(new Date().toISOString());
      setDraftState("saved");
    } catch (err) {
      // 503 = el entorno de ejecución (sandbox) no respondió: no es un error
      // en el código del estudiante, así que se muestra distinto (aviso para
      // reintentar, no como si su código estuviera mal) — ver
      // _raise_if_infra_error en el backend.
      const infraError = err.response?.status === 503;
      setOutput({
        stdout: "",
        stderr: infraError ? "" : err.response?.data?.detail || "Error al ejecutar el código.",
        infraError,
        infraMessage: infraError ? err.response?.data?.detail : null,
      });
    } finally {
      setRunning(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const result = await saveFn(problem.id, code);
      setSavedAt(result.saved_at);
      setCanSave(false);
      if (draftTimerRef.current) {
        clearTimeout(draftTimerRef.current);
        draftTimerRef.current = null;
      }
      setDraftState("saved");
    } catch (err) {
      setOutput((prev) => ({
        ...prev,
        stderr: err.response?.data?.detail || "Error al guardar la respuesta.",
      }));
    } finally {
      setSaving(false);
    }
  }

  const disabled = examFinished || loadingSaved;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] shadow-xl shadow-black/30 overflow-hidden">
      <div className="px-6 py-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
        <h3 className="text-white font-semibold">
          {index + 1}. {problem.title}
        </h3>
        <span className="text-xs text-slate-400 rounded-full border border-white/10 px-2.5 py-1">
          {problem.max_score} pts
        </span>
      </div>

      <div className="markdown-body px-6 py-5">
        <ReactMarkdown remarkPlugins={[remarkMath, remarkGfm]} rehypePlugins={[rehypeKatex]}>
          {problem.statement_md}
        </ReactMarkdown>
      </div>

      <div className="border-t border-white/10">
        <div className="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-black/40">
          <span className="text-xs text-slate-400 font-mono">celda_de_codigo.py</span>
          <span className="text-xs text-slate-500">Python 3</span>
        </div>
        <Editor
          height="340px"
          defaultLanguage="python"
          theme="vs-dark"
          value={code}
          onMount={(_editor, monaco) => registerPythonCompletions(monaco)}
          onChange={(value) => {
            const next = value ?? "";
            setCode(next);
            setCanSave(false);
            if (!disabled) scheduleDraftSave(next);
          }}
          options={{
            fontSize: 14,
            fontFamily: "JetBrains Mono, monospace",
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            padding: { top: 12 },
            readOnly: disabled,
          }}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3 px-6 py-4 bg-white/[0.02] border-t border-white/10">
        <button
          onClick={handleRun}
          disabled={running || disabled}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 transition text-white text-sm font-medium px-4 py-2 disabled:opacity-60"
        >
          ▶ {running ? "Ejecutando..." : "Ejecutar"}
        </button>

        {canSave && (
          <button
            onClick={handleSave}
            disabled={saving || disabled}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-brand-600 to-fuchsia-600 hover:from-brand-500 hover:to-fuchsia-500 transition text-white text-sm font-medium px-4 py-2 disabled:opacity-60"
          >
            {saving ? "Guardando..." : "Guardar respuesta"}
          </button>
        )}

        {savedAt && !canSave && (
          <span className="text-sm font-medium rounded-full px-3 py-1 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            ✓ Respuesta guardada
          </span>
        )}

        {!disabled && (
          <span className="text-xs text-slate-500 ml-auto">
            {draftState === "pending" && "Autoguardando en unos segundos…"}
            {draftState === "saving" && "Autoguardando…"}
            {draftState === "saved" && "✓ Código autoguardado"}
            {draftState === "error" && (
              <span className="text-rose-400">⚠ No se pudo autoguardar, revisa tu conexión</span>
            )}
          </span>
        )}
      </div>

      {output?.infraError && (
        <div className="px-6 py-4 border-t border-white/10 bg-amber-500/10">
          <p className="text-sm text-amber-300 font-medium">⚠ No se pudo conectar con el entorno de ejecución</p>
          <p className="text-sm text-amber-200/80 mt-1">
            {output.infraMessage || "Intenta ejecutar de nuevo en unos segundos."} Esto no tiene que ver con tu
            código — no perdiste tu última calificación guardada.
          </p>
          <button
            onClick={handleRun}
            disabled={running}
            className="mt-3 rounded-lg border border-amber-400/40 text-amber-300 hover:bg-amber-500/10 transition text-sm font-medium px-3 py-1.5 disabled:opacity-60"
          >
            {running ? "Reintentando..." : "Reintentar"}
          </button>
        </div>
      )}

      {output && !output.infraError && (
        <div className="px-6 py-4 border-t border-white/10 bg-black/30">
          <p className="text-xs uppercase tracking-wide text-slate-500 mb-2">Salida</p>
          {output.stdout && (
            <pre className="text-sm text-slate-200 font-mono whitespace-pre-wrap">{output.stdout}</pre>
          )}
          {output.stderr && (
            <pre className="text-sm text-rose-400 font-mono whitespace-pre-wrap mt-2">{output.stderr}</pre>
          )}
          {!output.stdout && !output.stderr && (!output.figures || output.figures.length === 0) && (
            <p className="text-sm text-slate-500 italic">Sin salida.</p>
          )}
        </div>
      )}

      {output?.figures && output.figures.length > 0 && (
        <div className="px-6 py-4 border-t border-white/10 bg-black/20 space-y-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            {output.figures.length > 1 ? "Gráficas" : "Gráfica"}
          </p>
          {output.figures.map((png, i) => (
            <img
              key={i}
              src={`data:image/png;base64,${png}`}
              alt={`Gráfica ${i + 1} generada por tu código`}
              className="max-w-full rounded-lg border border-white/10 bg-white"
            />
          ))}
        </div>
      )}

      {output && hideGrading && (
        <div className="px-6 py-3 border-t border-white/10 bg-amber-500/5">
          <p className="text-xs text-amber-400/90">
            🔒 La calificación y la solución de referencia se mostrarán cuando finalices el examen.
          </p>
        </div>
      )}

      {output?.checks && output.checks.length > 0 && (
        <div className="px-6 py-4 border-t border-white/10 bg-white/[0.02]">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Resultado de la calificación</p>
            <span className="text-sm font-semibold text-white">
              {output.total_score} / {output.max_score} pts
            </span>
          </div>
          <ul className="space-y-1.5">
            {output.checks.map((check, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className={check.passed ? "text-emerald-400" : "text-rose-400"}>
                  {check.passed ? "✓" : "✗"}
                </span>
                <span className={check.passed ? "text-slate-300" : "text-slate-400"}>
                  {check.label}{" "}
                  <span className="text-slate-500">
                    ({check.points}/{check.max_points} pts)
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {output?.solution_code && (
        <div className="border-t border-white/10">
          <div className="px-6 py-3 bg-white/[0.02]">
            <p className="text-xs uppercase tracking-wide text-slate-500">Solución de referencia</p>
          </div>
          <pre className="px-6 py-4 bg-black/40 text-sm text-slate-200 font-mono whitespace-pre-wrap overflow-x-auto">
            {output.solution_code}
          </pre>
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import * as api from "../api";
import ProblemCard from "../components/ProblemCard";

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

export default function ExamPage() {
  const { examId } = useParams();
  const [exam, setExam] = useState(null);
  const [remaining, setRemaining] = useState(null);
  const [loading, setLoading] = useState(true);
  const [finishing, setFinishing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const finishedRef = useRef(false);
  const navigate = useNavigate();

  // ---- Control de salidas de ventana (solo si el docente lo activó) ----
  const [violations, setViolations] = useState(0);
  const [warning, setWarning] = useState(null); // { violations, max } tras cada salida
  const [armed, setArmed] = useState(false); // ya entró a pantalla completa: desde aquí se cuentan salidas
  const [isFullscreen, setIsFullscreen] = useState(!!document.fullscreenElement);
  const maxViolations = exam?.max_violations || 0;
  const proctored = maxViolations > 0;
  const fullscreenSupported = !!document.documentElement.requestFullscreen;
  // Mientras no esté en pantalla completa (o, sin soporte, no haya aceptado
  // las reglas) el contenido del examen queda oculto detrás de un aviso.
  const gateOpen = proctored && (fullscreenSupported ? !isFullscreen : !armed);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const [examData, attempt] = await Promise.all([api.getExam(examId), api.startExam(examId)]);
        if (cancelled) return;

        if (attempt.finished) {
          navigate(`/exams/${examId}/results`, { replace: true });
          return;
        }

        setExam(examData);
        setViolations(attempt.violations || 0);
        setRemaining(attempt.remaining_seconds);
      } catch (err) {
        navigate("/exams");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [examId]);

  useEffect(() => {
    if (remaining === null) return;
    if (remaining <= 0) {
      handleAutoFinish();
      return;
    }
    const timer = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(timer);
          handleAutoFinish();
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining !== null]);

  async function enterFullscreen() {
    try {
      if (fullscreenSupported) await document.documentElement.requestFullscreen();
    } catch {
      /* el navegador rechazó la pantalla completa; el aviso sigue visible */
    }
    setIsFullscreen(!!document.fullscreenElement);
    setArmed(true);
  }

  useEffect(() => {
    if (!proctored || !armed) return;

    async function report(kind) {
      if (finishedRef.current) return;
      try {
        const attempt = await api.reportViolation(examId, kind);
        setViolations(attempt.violations);
        if (attempt.annulled) {
          finishedRef.current = true;
          navigate(`/exams/${examId}/results`, { replace: true });
        } else if (attempt.violations > 0) {
          setWarning({ violations: attempt.violations, max: attempt.max_violations });
        }
      } catch {
        /* sin conexión: el aviso no se pudo registrar */
      }
    }

    // Con la pantalla completa ya perdida (aviso abierto) no se cuentan más
    // salidas: ya se contó la de la propia pérdida de pantalla completa.
    const inFullscreen = () => !fullscreenSupported || !!document.fullscreenElement;
    const onVisibility = () => {
      if (document.hidden && inFullscreen()) report("hidden");
    };
    const onBlur = () => {
      if (inFullscreen()) report("blur");
    };
    const onFullscreenChange = () => {
      const active = !!document.fullscreenElement;
      setIsFullscreen(active);
      if (!active) report("fullscreen_exit");
    };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("fullscreenchange", onFullscreenChange);
      // Al salir de la pantalla del examen se devuelve la pantalla normal (ya sin escuchar).
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proctored, armed, examId]);

  async function handleAutoFinish() {
    if (finishedRef.current) return;
    finishedRef.current = true;
    try {
      await api.finishExam(examId);
    } finally {
      navigate(`/exams/${examId}/results`, { replace: true });
    }
  }

  async function confirmFinish() {
    setShowConfirm(false);
    setFinishing(true);
    finishedRef.current = true;
    try {
      await api.finishExam(examId);
      navigate(`/exams/${examId}/results`, { replace: true });
    } finally {
      setFinishing(false);
    }
  }

  if (loading || !exam) {
    return (
      <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center text-slate-400">
        Cargando examen...
      </div>
    );
  }

  const unlimited = exam.duration_minutes == null;
  const lowTime = remaining !== null && remaining <= 300;

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/exams" className="text-slate-400 hover:text-white text-sm">
            ← Exámenes
          </Link>
          <div className="flex-1">
            <h1 className="text-white font-semibold">{exam.title}</h1>
            <p className="text-slate-500 text-xs">{exam.description}</p>
          </div>

          {proctored && (
            <div
              className={`text-xs font-medium rounded-lg px-3 py-1.5 border ${
                violations > 0
                  ? "text-amber-300 border-amber-500/40 bg-amber-500/10"
                  : "text-slate-400 border-white/10 bg-white/5"
              }`}
              title="Salidas de la ventana del examen"
            >
              ⚠ Salidas {violations}/{maxViolations}
            </div>
          )}

          {unlimited ? (
            <div className="font-medium text-sm rounded-lg px-3 py-1.5 border text-sky-400 border-sky-500/30 bg-sky-500/10">
              ⏱ Sin límite de tiempo
            </div>
          ) : (
            <div
              className={`font-mono text-lg font-bold rounded-lg px-3 py-1.5 border ${
                lowTime
                  ? "text-rose-400 border-rose-500/40 bg-rose-500/10 animate-pulse"
                  : "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
              }`}
            >
              ⏱ {remaining !== null ? formatTime(remaining) : "--:--"}
            </div>
          )}

          <button
            onClick={() => setShowConfirm(true)}
            disabled={finishing}
            className="rounded-lg bg-gradient-to-r from-rose-600 to-orange-600 hover:from-rose-500 hover:to-orange-500 transition text-white text-sm font-medium px-4 py-2 disabled:opacity-60"
          >
            {finishing ? "Finalizando..." : "Finalizar cuestionario"}
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10 space-y-8 pb-24">
        {exam.problems.map((problem, i) => (
          <ProblemCard
            key={problem.id}
            problem={problem}
            index={i}
            examFinished={false}
            hideGrading={!unlimited}
          />
        ))}
      </main>

      {gateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0b0d17] px-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#12142a] p-7 shadow-2xl text-center">
            <h2 className="text-white font-semibold text-xl mb-3">Examen con control de ventana</h2>
            <p className="text-slate-300 text-sm mb-3">
              Debes mantener el examen en <span className="font-semibold">pantalla completa</span>. Cambiar de
              pestaña o de ventana, minimizar o salir de la pantalla completa cuenta como una salida.
            </p>
            <p className="text-rose-300 text-sm font-medium mb-3">
              Con {maxViolations} salidas el examen se anula y tu calificación será 0.
            </p>
            {violations > 0 && (
              <p className="text-amber-300 text-sm mb-3">
                Llevas {violations} de {maxViolations} salidas. El tiempo del examen sigue corriendo.
              </p>
            )}
            <button
              onClick={enterFullscreen}
              className="mt-2 w-full rounded-lg bg-gradient-to-r from-brand-600 to-fuchsia-600 hover:from-brand-500 hover:to-fuchsia-500 transition text-white font-medium px-4 py-2.5"
            >
              {violations > 0 || armed ? "Volver a pantalla completa" : "Entendido, iniciar en pantalla completa"}
            </button>
          </div>
        </div>
      )}

      {!gateOpen && warning && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm rounded-2xl border border-amber-500/40 bg-[#12142a] p-6 shadow-2xl">
            <h2 className="text-amber-300 font-semibold text-lg mb-2">
              Salida {warning.violations} de {warning.max}
            </h2>
            <p className="text-slate-300 text-sm mb-1">Saliste de la ventana del examen.</p>
            <p className="text-slate-400 text-sm mb-5">
              {warning.max - warning.violations === 1
                ? "Una salida más y tu examen se anulará con calificación 0."
                : `Te quedan ${warning.max - warning.violations} salidas antes de que tu examen se anule con calificación 0.`}
            </p>
            <div className="flex justify-end">
              <button
                onClick={() => setWarning(null)}
                className="rounded-lg bg-amber-600 hover:bg-amber-500 transition text-white text-sm font-medium px-4 py-2"
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}

      {showConfirm && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-[#12142a] p-6 shadow-2xl">
            <h2 className="text-white font-semibold text-lg mb-2">¿Finalizar cuestionario?</h2>
            <p className="text-slate-400 text-sm mb-6">
              No podrás modificar tus respuestas después de esto. Asegúrate de haber guardado todas tus
              respuestas.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/5 transition"
              >
                Cancelar
              </button>
              <button
                onClick={confirmFinish}
                className="rounded-lg bg-gradient-to-r from-rose-600 to-orange-600 hover:from-rose-500 hover:to-orange-500 transition text-white text-sm font-medium px-4 py-2"
              >
                Sí, finalizar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

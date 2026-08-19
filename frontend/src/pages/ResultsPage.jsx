import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import * as api from "../api";

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
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

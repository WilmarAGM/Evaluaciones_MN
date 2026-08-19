import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import * as api from "../api";

export default function ExamList() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api
      .getExams()
      .then(setExams)
      .catch(() => navigate("/"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-fuchsia-500 flex items-center justify-center text-white font-bold">
              ∑
            </div>
            <span className="text-white font-semibold">Métodos Numéricos</span>
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
        <h1 className="text-2xl font-bold text-white mb-1">Exámenes disponibles</h1>
        <p className="text-slate-400 mb-8">Selecciona un examen para comenzar.</p>

        {loading && <p className="text-slate-500">Cargando...</p>}

        <div className="grid gap-4 sm:grid-cols-2">
          {exams.map((exam) => {
            const locked = exam.status === "not_started" && !exam.is_open;

            const badge = locked
              ? { label: "No habilitado", cls: "bg-slate-500/15 text-slate-500 border-slate-500/30" }
              : {
                  not_started: { label: "No iniciado", cls: "bg-slate-500/15 text-slate-400 border-slate-500/30" },
                  in_progress: { label: "En progreso", cls: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
                  finished: { label: "Finalizado", cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
                }[exam.status];

            const cta = {
              not_started: "Comenzar →",
              in_progress: "Continuar →",
              finished: "Ver resultados →",
            }[exam.status];

            const to = exam.status === "finished" ? `/exams/${exam.id}/results` : `/exams/${exam.id}`;

            if (locked) {
              return (
                <div
                  key={exam.id}
                  className="rounded-2xl border border-white/5 bg-white/[0.02] p-5 opacity-60 cursor-not-allowed"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="text-lg font-semibold text-slate-400">{exam.title}</h2>
                    <span className={`shrink-0 text-xs font-medium rounded-full border px-2.5 py-1 ${badge.cls}`}>
                      {badge.label}
                    </span>
                  </div>
                  <p className="text-slate-500 text-sm mt-2">{exam.description}</p>
                  <p className="text-slate-500 text-sm mt-3">Tu docente aún no ha habilitado este examen.</p>
                </div>
              );
            }

            return (
              <Link
                key={exam.id}
                to={to}
                className="group rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-brand-400/40 transition p-5 shadow-lg shadow-black/20"
              >
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-lg font-semibold text-white group-hover:text-brand-300 transition">
                    {exam.title}
                  </h2>
                  <span className={`shrink-0 text-xs font-medium rounded-full border px-2.5 py-1 ${badge.cls}`}>
                    {badge.label}
                  </span>
                </div>
                <p className="text-slate-400 text-sm mt-2">{exam.description}</p>
                <p className="text-brand-300 text-sm mt-3 opacity-0 group-hover:opacity-100 transition">{cta}</p>
              </Link>
            );
          })}
        </div>

        {!loading && exams.length === 0 && (
          <p className="text-slate-500">No hay exámenes disponibles todavía.</p>
        )}
      </main>
    </div>
  );
}

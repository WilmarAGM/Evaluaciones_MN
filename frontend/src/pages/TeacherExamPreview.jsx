import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import * as api from "../api";
import ProblemCard from "../components/ProblemCard";

export default function TeacherExamPreview() {
  const { examId } = useParams();
  const [exam, setExam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getTeacherExamPreview(examId)
      .then((data) => {
        if (!cancelled) setExam(data);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar la previsualización de este examen.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [examId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center text-slate-400">
        Cargando previsualización...
      </div>
    );
  }

  if (error || !exam) {
    return (
      <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center text-rose-400">
        {error || "Examen no encontrado."}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/teacher/exams" className="text-slate-400 hover:text-white text-sm">
            ← Exámenes
          </Link>
          <div className="flex-1">
            <h1 className="text-white font-semibold">{exam.title}</h1>
            <p className="text-slate-500 text-xs">{exam.description}</p>
          </div>
          <div className="font-medium text-sm rounded-lg px-3 py-1.5 border text-amber-400 border-amber-500/30 bg-amber-500/10">
            👁 Modo previsualización (docente)
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10 space-y-8 pb-24">
        <p className="text-sm text-slate-400 -mt-2">
          Estás resolviendo este examen como docente: sin cronómetro y sin que cuente en las
          estadísticas de los estudiantes. Usa "Ejecutar" para validar cada respuesta contra la
          rúbrica real.
        </p>
        {exam.problems.map((problem, i) => (
          <ProblemCard
            key={problem.id}
            problem={problem}
            index={i}
            examFinished={false}
            runFn={api.teacherRunCode}
            saveFn={api.teacherSaveCode}
          />
        ))}
      </main>
    </div>
  );
}

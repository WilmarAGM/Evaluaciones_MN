import { SCIPY_ROUTINES } from "./scipyRoutines";

// numpy/math functions usadas típicamente en las rutinas del curso.
const NUMPY_FUNCS = [
  ["array", "array(${1:lista})"],
  ["linspace", "linspace(${1:a}, ${2:b}, ${3:n})"],
  ["zeros", "zeros(${1:n})"],
  ["exp", "exp(${1:x})"],
  ["log", "log(${1:x})"],
  ["sqrt", "sqrt(${1:x})"],
  ["sin", "sin(${1:x})"],
  ["cos", "cos(${1:x})"],
  ["tan", "tan(${1:x})"],
  ["arctan", "arctan(${1:x})"],
  ["arcsin", "arcsin(${1:x})"],
  ["arccos", "arccos(${1:x})"],
  ["abs", "abs(${1:x})"],
  ["pi", "pi"],
  ["isclose", "isclose(${1:a}, ${2:b})"],
];

let registered = false;

/**
 * Autocompletado estático para las celdas de código: sugiere los imports y
 * llamadas de rutinas reales de numpy/scipy/scikit-learn (ver
 * scipyRoutines.js) y funciones comunes de numpy. No es un language server
 * real (no entiende tipos), solo una lista curada — suficiente para no
 * obligar al estudiante a recordar nombres exactos de módulos/funciones/
 * argumentos.
 */
export function registerPythonCompletions(monaco) {
  if (registered) return;
  registered = true;

  monaco.languages.registerCompletionItemProvider("python", {
    triggerCharacters: [".", " "],
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      const suggestions = [];

      for (const r of SCIPY_ROUTINES) {
        const argNames = r.args
          .split(",")
          .map((a) => a.split("=")[0].trim())
          .filter(Boolean);
        const placeholders = argNames.map((a, i) => `\${${i + 1}:${a}}`).join(", ");

        suggestions.push({
          label: `from ${r.module} import ${r.func}`,
          kind: monaco.languages.CompletionItemKind.Module,
          insertText: `from ${r.module} import ${r.func}`,
          detail: `${r.func}(${r.args})`,
          documentation: r.desc || undefined,
          range,
        });

        suggestions.push({
          label: `${r.func}(...)`,
          kind: monaco.languages.CompletionItemKind.Function,
          insertText: `${r.func}(${placeholders})`,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          detail: `${r.func}(${r.args})`,
          documentation: r.desc || undefined,
          range,
        });
      }

      for (const [name, snippet] of NUMPY_FUNCS) {
        suggestions.push({
          label: `np.${name}`,
          kind: monaco.languages.CompletionItemKind.Function,
          insertText: `np.${snippet}`,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          detail: "numpy",
          range,
        });
      }

      suggestions.push({
        label: "import numpy as np",
        kind: monaco.languages.CompletionItemKind.Module,
        insertText: "import numpy as np",
        range,
      });

      return { suggestions };
    },
  });
}

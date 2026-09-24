"""Seguimiento de uso diario de la API de Gemini (Google AI Studio) — SOLO
informativo, para mostrarle al docente cuánto ha gastado hoy. Ya NO impone
un tope propio: la cuenta es de pago por uso, así que se deja llamar
libremente y quien avisa de un cupo agotado de verdad es Google (ver
QuotaExceededError, ahora usado para el 429/RESOURCE_EXHAUSTED real de la
API, no para un límite propio — ver gemini_agents._call_gemini).

Persiste el conteo del día en un archivo JSON simple (no hay concurrencia
real: esto lo corre el docente manualmente desde el panel)."""
import json
import os
import threading
from datetime import date

_LOCK = threading.Lock()
_QUOTA_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".gemini_quota.json"))


class QuotaExceededError(Exception):
    """Google respondió que de verdad se agotó el cupo/crédito de la API
    (429 RESOURCE_EXHAUSTED, tras los reintentos de errores transitorios) —
    ver _call_gemini. Ya no representa un límite propio: ver el docstring
    del módulo."""


def _today() -> str:
    return date.today().isoformat()


def _load() -> dict:
    if not os.path.exists(_QUOTA_PATH):
        return {}
    with open(_QUOTA_PATH) as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(_QUOTA_PATH, "w") as f:
        json.dump(data, f)


def get_usage_today() -> dict:
    return _load().get(_today(), {"calls": 0, "tokens": 0})


def record_call() -> None:
    with _LOCK:
        data = _load()
        today = _today()
        usage = data.get(today, {"calls": 0, "tokens": 0})
        usage["calls"] += 1
        data[today] = usage
        _save(data)


def record_tokens(n_tokens: int) -> None:
    with _LOCK:
        data = _load()
        today = _today()
        usage = data.get(today, {"calls": 0, "tokens": 0})
        usage["tokens"] += n_tokens
        data[today] = usage
        _save(data)
